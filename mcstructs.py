import os
import re
import subprocess

via_nbt_version = '5.0.0'
version_prefix = '5'

# All of this would work better with bytecode rewriting, but here we go
replacements = {
    # Gradle build script changes (less chance of running into conflicts by putting it here instead of the patch)
    'name = "lenni0451"': 'name = "viaversion"',
    'url = "https://maven.lenni0451.net/everything"': 'url = "https://repo.viaversion.com/"',
    'api project(":MCStructs-nbt")': f'api "com.viaversion:nbt:{via_nbt_version}"',
    'maven_group=net.lenni0451.mcstructs': 'maven_group=com.viaversion.mcstructs',
    'maven_version=': f'maven_version={version_prefix}-',
    # Code changes
    'import net.lenni0451.mcstructs.nbt.tags.': 'import com.viaversion.nbt.tag.',
    'import net.lenni0451.mcstructs.nbt.': 'import com.viaversion.nbt.tag.',
    'INbtTag': 'Tag',
    'INbtNumber': 'NumberTag',
    'tag.getNbtType()': 'tag',
    'ArrayTag.getLength()': 'ArrayTag.length()',
    'type.name()': 'type.getClass().getSimpleName()',
    'NbtType': 'Tag',
    'import com.viaversion.nbt.tag.Tag': 'import com.viaversion.nbt.tag.*',
    'import com.viaversion.nbt.tag.CompoundTag': 'import com.viaversion.nbt.tag.*',
    # A special one
    '            if (!list.canAdd(tag)) throw new SNbtDeserializeException("Unable to insert " + tag.getClass().getSimpleName() + " into ListTag of type " + list.getType().name());': ''
}

# Apply these separately to avoid changing json calls
extra_replacements = {
    '.addString(': '.putString(',
    '.addBoolean(': '.putBoolean(',
    '.addByte(': '.putByte(',
    '.addLong(': '.putLong(',
    '.addInt(': '.putInt(',
    '.addDouble(': '.putDouble(',
    '.addShort(': '.putShort(',
    '.addCompound(': '.put(',
    '.addAll(': '.putAll(',
    '.getTag().name()': '.getClass()',
    'tag.name()': 'tag.getClass()',
    'list.getType().isNumber()': 'list.getElementType().isAssignableFrom(com.viaversion.nbt.tag.NumberTag.class)',
    'values.get(i).asNumberTag().intValue()': '((NumberTag) values.get(i)).asInt()',
    'this.styleSerializer.serialize(object.getStyle()).asCompoundTag()': '(CompoundTag) this.styleSerializer.serialize(object.getStyle())',
    'JsonNbtConverter.toNbt(json).asCompoundTag()': '((CompoundTag) JsonNbtConverter.toNbt(json))',
    'Tag.COMPOUND.equals(list.getType())': 'CompoundTag.class == list.getElementType()',
    'Tag.COMPOUND.equals(listTag.getType())': 'CompoundTag.class == listTag.getElementType()',
    'compound.add(': 'compound.put(',
    '.numberValue()': '.getValue()',
    '(ACTION)': '("action")',
    '(CONTENTS, ': '("contents", ',
    '(CONTENTS)': '("contents")',
    'tags.get(0).getTag()': 'tags.get(0)',
    # Special ones
    '!type.equals(tags.get(i).getTag())': "type.getClass() != tags.get(i).getClass()",
    'String type = ((StringTag) tag.get("type")).getValue()': 'String type = tag.contains("type") ? ((StringTag) tag.get("type")).getValue() : null'
}


def main():
    os.chdir('MCStructs')

    handle_file('build.gradle')
    handle_file('gradle.properties')
    deep('MCStructs-snbt')
    deep('MCStructs-text')

    # Apply additional manual changes
    apply_patch('../patch.patch')


def apply_patch(patch_file):
    try:
        subprocess.run(['git', 'apply', '--reject', '--ignore-whitespace', '--ignore-space-change', patch_file],
                       check=True)
        print('Applied patch')
    except subprocess.CalledProcessError as e:
        print(f'Error applying patch: {e}')


def deep(path):
    for p in os.listdir(path):
        p = os.path.join(path, p)
        if os.path.isdir(p):
            deep(p)
        elif p.endswith(".java") or p.endswith(".gradle"):
            handle_file(p)


def to_camel_case(s):
    words = s.split('_')
    camel_case_words = [words[0].capitalize()] + [word.capitalize() for word in words[1:]]
    return ''.join(camel_case_words)


def replace_get_value(content, obj):
    # First apply nullable replacements with the generic replacement, THEN the rest
    content = replace_nullable_get(obj, 'Compound', '', 'null', content)
    content = replace_nullable_get(obj, 'List', '', 'null', content)
    content = re.sub(fr'{obj}\.get(\w+)\(([^,)]+), null\)',
                     fr'({obj}.get(\2) instanceof \1Tag ? ((\1Tag) {obj}.get(\2)).getValue() : null)',
                     content)

    content = replace_nonnull_get(obj, 'Compound', '', 'new CompoundTag()', content)
    content = replace_nonnull_get(obj, 'List', '', 'new ListTag<>()', content)
    content = replace_nonnull_get(obj, 'String', '.getValue()', '""', content)
    content = replace_nonnull_get(obj, 'ByteArray', '.getValue()', 'new byte[0]', content)
    content = replace_nonnull_get(obj, 'IntArray', '.getValue()', 'new int[0]', content)
    content = replace_nonnull_get(obj, 'LongArray', '.getValue()', 'new long[0]', content)

    # Booleans are stored as byte tags
    content = re.sub(fr'{obj}\.getBoolean\(([^)]+)\)',
                     fr'({obj}.get(\1) instanceof ByteTag ? ((ByteTag) {obj}.get(\1)).asBoolean() : false)',
                     content)

    # something.get(y).asXTag() -> ((XTag) something.get(y))
    content = re.sub(fr'{obj}\.get\(([^)]+)\).as(\w+Tag)\(\)',
                     fr'((\2) {obj}.get(\1))',
                     content)

    numeric_types = {'Byte', 'Short', 'Int', 'Long', 'Float', 'Double'}
    for numeric_type in numeric_types:
        content = replace_nonnull_get(obj, numeric_type, f'.as{numeric_type}()', '0', content)

    return content


def replace_nullable_get(obj, tag_type, value_method, default, content):
    pattern = re.compile(fr'{obj}\.get{tag_type}\(([^,)]+), null\)')
    replacement = fr'({obj}.get(\1) instanceof {tag_type}Tag ? (({tag_type}Tag) {obj}.get(\1)){value_method} : {default})'
    return pattern.sub(replacement, content)


def replace_nonnull_get(obj, tag_type, value_method, default, content):
    pattern = re.compile(fr'{obj}\.get{tag_type}\(([^)]+)\)')
    replacement = fr'({obj}.get(\1) instanceof {tag_type}Tag ? (({tag_type}Tag) {obj}.get(\1)){value_method} : {default})'
    return pattern.sub(replacement, content)


def handle_file(path):
    with open(path, 'r') as file:
        content = file.read()

    changed_content = content
    for old, new in replacements.items():
        changed_content = changed_content.replace(old, new)

    name = os.path.basename(path)
    if 'CompoundTag ' in changed_content:
        # Some are very explicit, so that they don't break random code elsewhere/make it look like it worked fine
        for old, new in extra_replacements.items():
            changed_content = changed_content.replace(old, new)

        if 'JsonHoverEventSerializer' not in name:
            changed_content = changed_content.replace('.add("', '.put("')

        # tag.isXTag() -> (tag instanceof XTag)
        changed_content = re.sub(r'(\w+)\.is(\w+Tag)\(\)', r'(\1 instanceof \2)', changed_content)

        # asXTag() -> cast
        changed_content = re.sub(r'(\w+)\.as(\w+Tag)\(\)', r'((\2) \1)', changed_content)
        changed_content = re.sub(r'tags.get\(i\)\.as(\w+Tag)\(\)', r'((\1) tags.get(i))', changed_content)

        # tag.contains(s, Tag.X) -> tag.get(s) instanceof XTag
        changed_content = re.sub(r'(\w+)\.contains\(([^,)]+), Tag\.(\w+)\)',
                                 lambda m: f'({m.group(1)}.get({m.group(2)}) instanceof {to_camel_case(m.group(3))}Tag)',
                                 changed_content)
        changed_content = re.sub(r'\.contains\(([^,)]+), Tag\.(\w+)\)',
                                 lambda m: f'.get({m.group(1)}) instanceof {to_camel_case(m.group(2))}Tag',
                                 changed_content)

        # Tag.X.equals(tagType) -> tagType instance XTag
        changed_content = re.sub(r'Tag\.(\w+).equals\((\w+)\)',
                                 lambda m: f'({m.group(2)} instanceof {to_camel_case(m.group(1))}Tag)',
                                 changed_content)

        # tag.getX -> cast to tag with default value
        changed_content = replace_get_value(changed_content, 'tag')
        changed_content = replace_get_value(changed_content, 'rawTag')
        changed_content = replace_get_value(changed_content, 'rawEntity')
        changed_content = replace_get_value(changed_content, 'score')
        changed_content = replace_get_value(changed_content, 'clickEvent')
        changed_content = replace_get_value(changed_content, 'parsed')

    if content == changed_content:
        return

    with open(path, 'w') as file:
        file.write(changed_content)

    print('Wrote to', path)


if __name__ == '__main__':
    main()
