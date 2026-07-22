# Model provider configuration

AgentSystem uses one independent model profile per Agent. A profile contains a provider preset, editable model ID, API format, Base URL, credential reference, timeout, output-token limit, budget metadata, and call mode.

## Provider presets

The built-in registry currently includes:

| Provider | Default API format | Default endpoint | Credential |
| --- | --- | --- | --- |
| Simulated | Responses-shaped local result | none | none |
| OpenAI | Responses API | `https://api.openai.com/v1` | required |
| DeepSeek | Chat Completions | `https://api.deepseek.com` | required |
| Qwen / DashScope | Chat Completions | `https://dashscope.aliyuncs.com/compatible-mode/v1` | required |
| Local vLLM | Chat Completions | `http://127.0.0.1:8001/v1` | optional |
| Custom OpenAI-compatible | Responses or Chat Completions | operator supplied | required |

Presets provide defaults, not a closed catalog. The model field and Base URL remain editable so an enterprise gateway, a newly released model, or a private deployment can be used without a code change.

## Safe activation flow

1. Open **Agent Studio** and choose an Agent.
2. Select a provider. The UI fills its default model, endpoint, API format, and live mode.
3. Add an API key under **Secure credentials**. The plaintext is sent once to the local API and stored in macOS Keychain; SQLite receives only an opaque reference and fingerprint.
4. Select the credential and use **Fetch models** to test authentication and retrieve `/models` without generating tokens.
5. Keep the discovered selection or enter a model ID manually, then use **Validate** and **Save**.
6. Repeat for each Agent that needs a different provider, model, or key.

Simulation remains available per Agent. A live profile never falls back silently: missing credentials, unsupported API formats, invalid endpoints, authentication failures, rate limits, and timeouts produce stable error codes in the task and trace.

## CC Switch ideas adapted here

The configuration workflow follows useful patterns from [farion1231/cc-switch](https://github.com/farion1231/cc-switch): provider presets coexist with custom endpoints, API format is explicit, model discovery uses endpoint candidates instead of hard-coded model choices, and stale discovery results are discarded when the provider changes. AgentSystem adds per-Agent versioning, Keychain references, audit traces, and deterministic workflow failure semantics required by the code collaboration runtime.
