# jammin + All SDKs (Undecided Template)

This project was created with [jammin](https://github.com/FluffyLabs/jammin), FluffyLabs' toolbox for JAM service builders.

## What is jammin?

Learn more about jammin in the [official documentation](https://fluffylabs.dev/jammin/). This is the **undecided template** - a starter template that includes example services for all available SDKs, perfect for exploring your options.

## What's Included

This project includes example services for all three SDKs:
- **JAM SDK** service in `services/example-jamsdk`
- **Jade SDK** service in `services/example-jade`
- **JamBrains SDK** service in `services/example-jambrains`

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
    ├── example-jamsdk/        # JAM SDK service
    ├── example-jade/          # Jade SDK service
    └── example-jambrains/     # JamBrains SDK service
```

## Learn More

- [jammin on github](https://github.com/FluffyLabs/jammin)
- [jammin on npm](https://www.npmjs.com/package/@fluffylabs/jammin)
- [jam sdk](https://docs.rs/jam-pvm-common/latest/jam_pvm_common/index.html)
- [jam types](https://docs.rs/jam-types/latest/jam_types/)
- [jambrains sdk](https://github.com/JamBrains/service-sdk)
- [jade sdk](https://github.com/spacejamapp/jade)
- [ajanda sdk](https://github.com/Chainscore/ajanta)

## Next Steps

1. Explore the different SDK examples in `services/`
2. Run `jammin build` to build all services
3. Choose the SDK that works best for you
4. Remove the services you don't need
5. Customize your chosen service
