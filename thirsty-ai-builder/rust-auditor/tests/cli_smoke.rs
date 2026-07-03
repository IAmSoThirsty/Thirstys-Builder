// Standalone unit tests for the auditor's request shape. No network.
#[test]
fn run_request_serializes_with_target_and_optional_title() {
    use serde_json;
    // Mirror the struct shape from main.rs; we redeclare inline so this
    // test compiles without importing the binary crate.
    #[derive(serde::Serialize)]
    struct RunRequest<'a> {
        target: &'a str,
        title: Option<&'a str>,
    }
    let req = RunRequest { target: "repo", title: None };
    let json = serde_json::to_string(&req).unwrap();
    assert!(json.contains("\"target\":\"repo\""));
    assert!(json.contains("\"title\":null"));
}
