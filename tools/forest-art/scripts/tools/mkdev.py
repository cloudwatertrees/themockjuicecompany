"""Make ArtDev.swift: the repo file's code with layer data loaded at runtime from $ART_DATA_DIR."""
import re, sys
src, out = sys.argv[1], sys.argv[2]
text = open(src).read()
code = text[:text.index('// MARK: - Layer data')]
names = re.findall(r'static let (\w+): String = """', text)
ext = ['extension ForestPathArt {']
for n in names:
    ext.append(f'    static let {n}: String = devLoad("{n}")')
ext.append('}')
ext.append('func devLoad(_ name: String) -> String {')
ext.append('    let dir = ProcessInfo.processInfo.environment["ART_DATA_DIR"]!')
ext.append('    return try! String(contentsOfFile: dir + "/" + name + ".txt", encoding: .utf8)')
ext.append('}')
open(out, 'w').write(code + '\n'.join(ext) + '\n')
