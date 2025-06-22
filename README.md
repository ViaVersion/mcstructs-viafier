Replaces mcstruct's inbuilt nbt library with ViaNBT.

## Setup

```bash
git submodule update --init
```

Then you can run the Python script to apply the automated updates.

```bash
py apply.py
cd MCStructs
gradlew test
```

## Development

Use `-d` (`--dev-mode`) to prepare for doing patch changes:
```bash
py apply.py -d
```
Run this to rebuild the patch:
```bash
py rebuild.py
```

## Dependency

We wouldn't necessarily recommend depending on this given the hacky replacements
and specific needs, but this is published to our maven repository at: https://repo.viaversion.com

```kotlin
implementation("com.viaversion.mcstructs:text:5-<mcstructs version>")
```

The prefix is the current major version of ViaVersion, followed by the mcstructs version.