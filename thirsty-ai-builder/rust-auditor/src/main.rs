//! Commander Auditor CLI.
//!
//! Posts a governance-audit request to a running ThirstyAi Builder
//! Commander backend. Designed to be invoked from a CI runner. The
//! backend stores the request, runs `verify_all.py` against the
//! target, and returns a signed-PDF audit ID.
//!
//! Usage:
//!   commander-auditor --api <base-url> --target <name> --api-key <token>
//!
//! The API key is supplied via the `CB_API` env var by the bundled
//! GitHub Actions workflow; pass `--api-key` for local runs.

use std::env;
use std::process::ExitCode;

use serde::{Deserialize, Serialize};
use ureq::Agent;

#[derive(Serialize)]
struct RunRequest<'a> {
    target: &'a str,
    title: Option<&'a str>,
}

#[derive(Deserialize, Debug)]
struct RunResponse {
    id: String,
    sha256: String,
}

struct Args {
    api: String,
    target: String,
    api_key: String,
    title: Option<String>,
}

fn parse_args() -> Result<Args, String> {
    let mut api: Option<String> = None;
    let mut target: Option<String> = None;
    let mut api_key: Option<String> = None;
    let mut title: Option<String> = None;

    let mut iter = env::args().skip(1);
    while let Some(flag) = iter.next() {
        match flag.as_str() {
            "--api" => api = iter.next(),
            "--target" => target = iter.next(),
            "--api-key" => api_key = iter.next(),
            "--title" => title = iter.next(),
            "--help" | "-h" => {
                eprintln!(
                    "Usage: commander-auditor --api <base-url> --target <name> \
                     [--api-key <token>] [--title <title>]\n\
                     Environment: CB_API may supply the base URL; \
                     CB_API_KEY may supply the API key."
                );
                std::process::exit(0);
            }
            other => return Err(format!("unknown flag: {other}")),
        }
    }

    let api = api
        .or_else(|| env::var("CB_API").ok())
        .ok_or_else(|| "missing --api (or CB_API env var)".to_string())?;
    let target = target.ok_or_else(|| "missing --target".to_string())?;
    let api_key = api_key
        .or_else(|| env::var("CB_API_KEY").ok())
        .unwrap_or_default();

    Ok(Args { api, target, api_key, title })
}

fn main() -> ExitCode {
    let args = match parse_args() {
        Ok(a) => a,
        Err(e) => {
            eprintln!("error: {e}");
            return ExitCode::from(2);
        }
    };

    let endpoint = format!("{}/api/commander/audits/run", args.api.trim_end_matches('/'));
    let body = RunRequest { target: &args.target, title: args.title.as_deref() };
    let agent: Agent = ureq::AgentBuilder::new().build();

    let mut req = agent.post(&endpoint).set("Content-Type", "application/json");
    if !args.api_key.is_empty() {
        req = req.set("Authorization", &format!("Bearer {}", args.api_key));
    }

    match req.send_string(&serde_json::to_string(&body).unwrap()) {
        Ok(resp) => match resp.into_json::<RunResponse>() {
            Ok(parsed) => {
                println!("audit_id={}", parsed.id);
                println!("sha256={}", parsed.sha256);
                println!("status=ok");
                ExitCode::SUCCESS
            }
            Err(e) => {
                eprintln!("error: failed to parse response: {e}");
                ExitCode::from(1)
            }
        },
        Err(e) => {
            eprintln!("error: audit request failed: {e}");
            ExitCode::from(1)
        }
    }
}
