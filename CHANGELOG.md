# Changelog

## [1.3.4](https://github.com/roquerodrigo/ha-neakasa-litterbox/compare/v1.3.3...v1.3.4) (2026-08-07)


### Bug Fixes

* **deps:** bump neakasa-litterbox-sdk to 0.2.2 ([b8dc821](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/b8dc8213bcf1a3f0ec615018e4490f3b2aef490b))


### Tests

* fail when the manifest and dev-group SDK pins drift ([a554c17](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/a554c173c4060d9d1456da715ccab7305397b646))

## [1.3.3](https://github.com/roquerodrigo/ha-neakasa-litterbox/compare/v1.3.2...v1.3.3) (2026-08-07)


### Bug Fixes

* abort reauth and reconfigure when credentials belong to another account ([24d837b](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/24d837bcdf438fc26ef39ff53c17ac523015e9e3))
* bind the SDK session, push supervisor and coordinator to the entry lifecycle ([47b06d1](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/47b06d1a8d09ccb89cf71fb79fdc1a6191a8490e))


### Code Refactoring

* remove blueprint leftovers and split data and entity modules into packages ([0c24e36](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/0c24e364ed712efd24076907382a285eb6f74be0))


### Dependencies

* bump the paired Home Assistant pins to 2026.8.0 ([b30d598](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/b30d598b25ff758d69f725e4b939c90300b7c1db))


### Development Dependencies

* **deps-dev:** Bump ruff ([a216280](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/a2162804fe39b9b2d46e9820449ce760130e8d37))


### Documentation

* describe the code as it is and make quality scale claims honest ([414fdbe](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/414fdbee8e1579e2de74ac12d7201ae951365619))


### Continuous Integration

* run checks on pull requests targeting any branch ([7e46bff](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/7e46bffcc01e770429bdcd390accacaece7bc5d0))
* run code scanning on pull requests targeting any branch ([9af7732](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/9af7732600b8384644328138785bd21cc34ac1d8))


### Miscellaneous Chores

* move CI to the shared workflows repository ([6c40e2f](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/6c40e2f38c12cbcf3b7028a724154462a89201ef))
* release on every conventional commit type ([71ee60e](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/71ee60e18a6aa0013ea0dd5e8e73991cfaa7837e))
* repair scripts/setup and pin pre-commit hooks to the project toolchain ([92b6bef](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/92b6befe8621c604a18c8875cfe3caa382ec84ef))

## [1.3.2](https://github.com/roquerodrigo/ha-neakasa-litterbox/compare/v1.3.1...v1.3.2) (2026-08-02)


### Bug Fixes

* recover automatically when a cloud request times out ([3e49d9c](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/3e49d9cb23ea7c38049f0a08867d80025c702021))

## [1.3.1](https://github.com/roquerodrigo/ha-neakasa-litterbox/compare/v1.3.0...v1.3.1) (2026-08-02)


### Bug Fixes

* sign in again when the cloud drops the session ([f7dc675](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/f7dc675108c7d0a649cbb3545d0e21aecd879fab))

## [1.3.0](https://github.com/roquerodrigo/ha-neakasa-litterbox/compare/v1.2.4...v1.3.0) (2026-08-01)


### Features

* allow removing devices the cloud no longer reports ([7b070cc](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/7b070ccef22b7dd2a7c0ceb3f9d766b67fb72baa))

## [1.2.4](https://github.com/roquerodrigo/ha-neakasa-litterbox/compare/v1.2.3...v1.2.4) (2026-08-01)


### Bug Fixes

* verify the MQTT broker's TLS chain ([f9725f9](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/f9725f94f7955c2ac3c0a8d779f8a37af6cf5c81))


### Documentation

* update CLAUDE.md ([1e9f364](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/1e9f364066e5b64e9eb78763d1870b463e43c951))

## [1.2.3](https://github.com/roquerodrigo/ha-neakasa-litterbox/compare/v1.2.2...v1.2.3) (2026-07-15)


### Bug Fixes

* **deps:** bump neakasa-litterbox-sdk to 0.1.12 ([03b1516](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/03b151602eccd95bec1136b23b220a19c179d4d5))
* **deps:** bump neakasa-litterbox-sdk to 0.1.12 ([a120c7a](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/a120c7ae6b35686c1a365d7ea2c3d461081c9832))

## [1.2.2](https://github.com/roquerodrigo/ha-neakasa-litterbox/compare/v1.2.1...v1.2.2) (2026-06-23)


### Bug Fixes

* discover EU devices via regional Aliyun gateway (SDK 0.1.11) ([717e5b7](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/717e5b73982d32ae16bdf96957653b2648fd1fd7))
* discover EU devices via regional Aliyun gateway (SDK 0.1.11) ([b430ff8](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/b430ff82698c98fbd9fab26696a3683eff2b2794))

## [1.2.1](https://github.com/roquerodrigo/ha-neakasa-litterbox/compare/v1.2.0...v1.2.1) (2026-06-22)


### Bug Fixes

* EU login — bump neakasa-litterbox-sdk to 0.1.10 ([735a3fc](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/735a3fc1b59f568be44a5d9fcb7aac3c2da7c0bb))

## [1.2.0](https://github.com/roquerodrigo/ha-neakasa-litterbox/compare/v1.1.0...v1.2.0) (2026-06-01)


### Features

* add "Cat appears" state to the Status sensor (SDK 0.1.9) ([7e58330](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/7e583303d4dce0c9614b243754cc3a0858b38be6))
* map operating_state "cat_appears" (cat inside) in the Status sensor ([00868dd](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/00868ddee1bfdda305066855e819641f89bd7b00))

## [1.1.0](https://github.com/roquerodrigo/ha-neakasa-litterbox/compare/v1.0.6...v1.1.0) (2026-06-01)


### Features

* add operating-state (Status) sensor + keep entities alive mid-cycle ([b6096f5](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/b6096f53beb1c47bf3ce6b4f586583a3367e2d38))
* add operating-state sensor + keep entities alive mid-cycle ([0fae620](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/0fae620f9dd6b25fdf3d0278895fdc8f5a5d37c4))

## [1.0.6](https://github.com/roquerodrigo/ha-neakasa-litterbox/compare/v1.0.5...v1.0.6) (2026-06-01)


### Bug Fixes

* **deps:** bump neakasa-litterbox-sdk to 0.1.6 ([088eb4a](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/088eb4abb71107a75746d82c3e55534296251635))
* **deps:** bump neakasa-litterbox-sdk to 0.1.6 ([9993daf](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/9993daf662f2c8cd16b0a7f9bd8440863153b5f5))

## [1.0.5](https://github.com/roquerodrigo/ha-neakasa-litterbox/compare/v1.0.4...v1.0.5) (2026-05-25)


### Documentation

* fix CI badge and drop license badge ([028bed0](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/028bed0134eb66f65bf4283ccb861c7a7ce32923))
* fix CI badge and drop license badge ([eb5748b](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/eb5748b437ae9389750d3a693b8fe23f30d2c973))

## [1.0.4](https://github.com/roquerodrigo/ha-neakasa-litterbox/compare/v1.0.3...v1.0.4) (2026-05-24)


### Bug Fixes

* **setup:** catch all non-auth errors as ConfigEntryNotReady ([3df3dfa](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/3df3dfa53c5128c56e4ef37b4fab183b7a6a6ec5))
* **setup:** catch all non-auth errors as ConfigEntryNotReady ([cc3d52b](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/cc3d52b570fe9c4700b8fc98574656926ab6f7ea))

## [1.0.3](https://github.com/roquerodrigo/ha-neakasa-litterbox/compare/v1.0.2...v1.0.3) (2026-05-22)


### Bug Fixes

* **binary_sensor:** clear "needs cleaning" once a clean runs after the visit ([645aa9c](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/645aa9cd97c41150a764ee0b6c56708515e91f1f))

## [1.0.2](https://github.com/roquerodrigo/ha-neakasa-litterbox/compare/v1.0.1...v1.0.2) (2026-05-22)


### Bug Fixes

* **deps:** bump neakasa-litterbox-sdk to 0.1.3 ([9e58d4a](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/9e58d4a5ca2319786d75667f28257d87b54eb35f))

## [1.0.1](https://github.com/roquerodrigo/ha-neakasa-litterbox/compare/v1.0.0...v1.0.1) (2026-05-21)


### Bug Fixes

* auto-reconnect MQTT push and retry transient coordinator errors ([26dc435](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/26dc435173546ce2ee30e46391f4d4f2cb41a055))
* **deps:** bump neakasa-litterbox-sdk to 0.1.2 ([d1d2c7e](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/d1d2c7ecd8ce7d76678bdb16fddd099b2ba8ecc8))

## [1.0.0](https://github.com/roquerodrigo/ha-neakasa-litterbox/compare/v0.1.3...v1.0.0) (2026-05-20)


### Features

* replace blueprint with Neakasa Litterbox cloud integration ([d56641d](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/d56641db5175e988afe83fdfa082e54851c53b89))


### Bug Fixes

* **ci:** unblock hassfest, release-please and HACS validation ([af7a47c](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/af7a47c8791abc7f296d958ac488f25011db5163))


### Miscellaneous Chores

* bump to 1.0.0 ([11f83b3](https://github.com/roquerodrigo/ha-neakasa-litterbox/commit/11f83b3acb6fa97995957507733d72285830a923))

## Changelog
