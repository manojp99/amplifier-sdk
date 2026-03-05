---
bundle:
  name: amplifier-sdk
  version: 1.0.0
  description: TypeScript SDK and Python runtime for the Amplifier agent framework

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  - bundle: git+https://github.com/kenotron-ms/engram-lite@main#subdirectory=behaviors/engram-lite.yaml
---

# Amplifier SDK

@foundation:context/shared/common-system-base.md
