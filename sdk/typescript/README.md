# TypeScript SDK

This dependency-free SDK uses the platform `fetch` API and preserves the same
server-side authorization semantics as the Python SDK. It does not synthesize
successful decisions.

```ts
import { BuilderClient } from "./client";

const client = new BuilderClient("http://127.0.0.1:8080");
const decision = await client.execute({
  request_id: "req-1",
  subject_id: "operator",
  operation: "echo",
  resource: "demo",
  parameters: { message: "hello" },
});
```
