import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.FileVisitOption
import java.nio.file.FileVisitResult
import java.nio.file.SimpleFileVisitor
import java.nio.file.attribute.BasicFileAttributes
import java.nio.charset.StandardCharsets
import java.security.MessageDigest

/** Content identity for declared resources, computed before task-cache lookup.
 * Only a small serializable value is passed into the process. Resource bytes
 * remain in their original directory input; no per-file staging is required.
 */
class ResourceIdentity {
    /** Enumerate through NIO, never glob/line parsing. Follow linked resources
     * (including external targets), but fail closed on cycles, dangling links,
     * unreadable entries and special files. Root aliases have the same identity.
     * Resources must remain immutable from capture through task completion.
     */
    static List<Path> entries(Path root) {
        def base = root.toAbsolutePath().normalize()
        List<Path> result = []
        Files.walkFileTree(base, EnumSet.of(FileVisitOption.FOLLOW_LINKS), Integer.MAX_VALUE,
            new SimpleFileVisitor<Path>() {
                @Override
                FileVisitResult preVisitDirectory(Path path, BasicFileAttributes attrs) {
                    result.add(path)
                    return FileVisitResult.CONTINUE
                }
                @Override
                FileVisitResult visitFile(Path path, BasicFileAttributes attrs) {
                    if (!attrs.isRegularFile())
                        throw new IllegalArgumentException('Resource member is not a regular file: ' + path)
                    result.add(path)
                    return FileVisitResult.CONTINUE
                }
            })
        return result
    }

    static List<Path> members(Path root) {
        return entries(root).findAll { Files.isRegularFile(it) }
    }

    static Map capture(Path root) {
        def paths = entries(root)
        def result = capture(root, paths.findAll { Files.isRegularFile(it) })
        def base = root.toAbsolutePath().normalize()
        def layout = MessageDigest.getInstance('SHA-256')
        for (Path entry : paths.sort { a, b -> base.relativize(a).toString() <=> base.relativize(b).toString() }) {
            // Ignore the spelling of a root alias; retain member link topology.
            String link = entry != base && Files.isSymbolicLink(entry) ? Files.readSymbolicLink(entry).toString() : ''
            String kind = Files.isDirectory(entry) ? 'directory' : 'file'
            String permissions = Files.getPosixFilePermissions(entry).collect { it.name() }.sort().join(',')
            for (String field : [base.relativize(entry).toString(), kind, link, permissions]) {
                layout.update(field.getBytes(StandardCharsets.UTF_8))
                layout.update((byte) 0)
            }
        }
        layout.update(result.sha256.getBytes(StandardCharsets.UTF_8))
        result.schema_version = 2
        result.algorithm = 'sha256-files-v1-layout-posix-v2'
        result.entry_count = paths.size()
        result.sha256 = layout.digest().encodeHex().toString()
        return result
    }

    static Map capture(Path root, Collection<Path> members) {
        def base = root.toAbsolutePath().normalize()
        def paths = members.collect { it.toAbsolutePath().normalize() }
        if (paths.toSet().size() != paths.size())
            throw new IllegalArgumentException('Duplicate resource member path')
        paths = paths.sort { a, b -> base.relativize(a).toString() <=> base.relativize(b).toString() }
        def tree = MessageDigest.getInstance('SHA-256')
        byte[] buffer = new byte[1024 * 1024]
        long total = 0
        for (Path member : paths) {
            def relative = base.relativize(member).toString().replace(File.separatorChar, '/' as char)
            if (relative == '..' || relative.startsWith('../'))
                throw new IllegalArgumentException('Resource member outside declared root')
            if (!Files.isRegularFile(member))
                throw new IllegalArgumentException('Resource member is not a regular file: ' + member)
            def before = Files.readAttributes(member, BasicFileAttributes)
            def content = MessageDigest.getInstance('SHA-256')
            long length = 0
            Files.newInputStream(member).withCloseable { stream ->
                int count
                while ((count = stream.read(buffer)) != -1) {
                    content.update(buffer, 0, count)
                    length += count
                }
            }
            def after = Files.readAttributes(member, BasicFileAttributes)
            if (before.size() != length || before.size() != after.size() ||
                before.lastModifiedTime() != after.lastModifiedTime() || before.fileKey() != after.fileKey())
                throw new IllegalStateException('Resource changed while fingerprinting: ' + member)
            for (String field : [relative, Long.toString(length), content.digest().encodeHex().toString()]) {
                tree.update(field.getBytes(StandardCharsets.UTF_8))
                tree.update((byte) 0)
            }
            total += length
        }
        return [schema_version: 1, algorithm: 'sha256-relative-path-size-file-sha256-v1',
                file_count: paths.size(), bytes: total, sha256: tree.digest().encodeHex().toString()]
    }
}
