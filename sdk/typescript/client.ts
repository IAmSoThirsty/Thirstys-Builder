export type ExecuteRequest = {
  request_id: string;
  subject_id: string;
  operation: string;
  resource: string;
  parameters?: Record<string, unknown>;
};

export class BuilderClient {
  constructor(private readonly baseUrl: string) {}

  health(): Promise<unknown> {
    return this.request("GET", "/health");
  }

  replay(): Promise<unknown> {
    return this.request("GET", "/v1/replay");
  }

  audit(): Promise<unknown> {
    return this.request("GET", "/v1/audit");
  }

  query(query: string): Promise<unknown> {
    return this.request("POST", "/v1/query", { query });
  }

  grpcCompat(method: string, payload: Record<string, unknown> = {}): Promise<unknown> {
    return this.request("POST", "/v1/grpc", { method, payload });
  }

  execute(request: ExecuteRequest): Promise<unknown> {
    return this.request("POST", "/v1/execute", request);
  }

  private async request(method: string, path: string, body?: unknown): Promise<unknown> {
    const response = await fetch(`${this.baseUrl.replace(/\/$/, "")}${path}`, {
      method,
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(`${response.status}: ${JSON.stringify(payload)}`);
    }
    return payload;
  }
}
