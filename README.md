Replaces mcstruct's inbuilt nbt library with ViaNBT.

## Setup

```bash
git submodule update --init
```

Then you can run the Python script to apply the automated updates.

```bash
py mcstructs.py
cd MCStructs
gradlew test -x checkstyleMain
```

## Dependency

We wouldn't necessarily recommend depending on this given the hacky replacements
and specific needs, but this is published to our maven repository at: https://repo.viaversion.com

```kotlin
implementation("com.viaversion.mcstructs:text:5-<mcstructs version>")
```

The prefix is the current major version of ViaVersion, followed by the mcstructs version.