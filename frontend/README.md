# Frontend

Expo/React Native client for the Care Allocation Scheduler prototype. See the
[repository README](../README.md) for setup, demo credentials, testing, and
security limitations.

Common commands:

```sh
npm ci
npm start
npm run web
node --test
```

Copy `.env.example` to `.env.local` only when the API is not reachable at the
default `http://127.0.0.1:8000`. Variables prefixed with `EXPO_PUBLIC_` are
embedded in the client and must never contain secrets.
