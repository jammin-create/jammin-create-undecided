# jammin + All SDKs (Undecided Template)

This project was created with [jammin](https://github.com/FluffyLabs/jammin), FluffyLabs' toolbox for JAM service builders.

## What is jammin?

Learn more about jammin in the [official documentation](https://fluffylabs.dev/jammin/). This is the **undecided template** - a starter template that includes example services for all available SDKs, perfect for exploring your options.

## What's Included

This project includes example services for all available SDKs:
- **JAM SDK** service in `services/example-jamsdk`
- **Jade SDK** service in `services/example-jade`
- **JamBrains SDK** service in `services/example-jambrains`
- **Ajanta SDK** service in `services/example-ajanta`
- **JAMC3 SDK** service in `services/example-jamc3`
- **as-lan SDK** service in `services/example-aslan`

Use this template to experiment with different SDKs and choose the one that best fits your needs.

## Getting Started

First, install the jammin CLI tool by following the [installation guide](https://fluffylabs.dev/jammin/getting-started.html).

Explore the different SDK examples:
- Build configuration via `jammin.build.yml`
- Ready-to-use development environment for all SDKs
- Compare and contrast different approaches

## Available Commands

### Build Services

```bash
jammin build
```

Builds all services defined in your `jammin.build.yml` configuration.

### Run Tests

```bash
jammin test
```

Runs unit tests for your services.

## Project Structure

```
.
├── jammin.build.yml           # jammin configuration
└── services/
    ├── example-ajanta/        # Ajanta SDK service
    ├── example-aslan/         # as-lan (AssemblyScript) SDK service
    ├── example-jade/          # Jade SDK service
    ├── example-jambrains/     # JamBrains SDK service
    ├── example-jamc3/         # JAMC3 (C3) SDK service
    └── example-jamsdk/        # JAM SDK service
```

## Learn More

- [jammin on github](https://github.com/FluffyLabs/jammin)
- [jammin on npm](https://www.npmjs.com/package/@fluffylabs/jammin)
- [jam sdk](https://docs.rs/jam-pvm-common/latest/jam_pvm_common/index.html)
- [jam types](https://docs.rs/jam-types/latest/jam_types/)
- [jambrains sdk](https://github.com/JamBrains/service-sdk)
- [jade sdk](https://github.com/spacejamapp/jade)
- [ajanta sdk](https://github.com/Chainscore/ajanta)
- [jamc3 sdk](https://github.com/DrEverr/jamc3.c3l)
- [as-lan sdk](https://github.com/tomusdrw/as-lan)

## Next Steps

1. Explore the different SDK examples in `services/`
2. Run `jammin build` to build all services
3. Choose the SDK that works best for you
4. Remove the services you don't need
5. Customize your chosen service

## Template auto-sync

Service directories under `services/example-*` and their SDK pins in
`jammin.build.yml` are kept in sync with the per-SDK source repos in the
`jammin-create` GitHub organization by the workflow at
`.github/workflows/sync-templates.yml`.

The workflow runs daily and can be triggered manually from the Actions
tab. It opens a PR on the branch `sync/templates` whenever a source repo
has drifted.

To set it up on a fork, configure two repo secrets from a GitHub App
installed on this repo with `contents: write` and `pull-requests: write`:

- `APP_ID` — the App's numeric ID
- `APP_PRIVATE_KEY` — the App's PEM private key

The list of sources is in `.github/sync-config.yml`.
