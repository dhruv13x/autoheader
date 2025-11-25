
from pathlib import Path
from unittest.mock import patch
from autoheader.filesystem import read_file_lines, write_file_content, get_file_hash, load_gitignore_patterns, find_configured_files, save_cache, load_cache
from autoheader.models import LanguageConfig


def test_read_file_lines_success(fs):
    fs.create_file("test.txt", contents="hello\nworld")
    lines = read_file_lines(Path("test.txt"))
    assert lines == ["hello", "world"]


def test_read_file_lines_os_error():
    with patch("pathlib.Path.open", side_effect=OSError("Permission denied")):
        lines = read_file_lines(Path("test.txt"))
        assert lines == []


def test_read_file_lines_unexpected_error():
    with patch("pathlib.Path.open", side_effect=Exception("Unexpected error")):
        lines = read_file_lines(Path("test.txt"))
        assert lines == []


def test_write_file_content_success(fs):
    path = Path("test.txt")
    fs.create_file(path)
    write_file_content(path, "hello", "world", False, False)
    assert path.read_text() == "hello"


def test_write_file_content_backup(fs):
    path = Path("test.txt")
    fs.create_file(path, contents="world")
    write_file_content(path, "hello", "world", True, False)
    assert path.read_text() == "hello"
    assert Path("test.txt.bak").read_text() == "world"


def test_write_file_content_dry_run(fs):
    path = Path("test.txt")
    write_file_content(path, "hello", "world", False, True)
    assert not path.exists()


def test_get_file_hash_io_error():
    with patch("builtins.open", side_effect=IOError("File not found")):
        assert get_file_hash(Path("non_existent_file.txt")) == ""


def test_load_gitignore_patterns_not_found(fs):
    patterns = load_gitignore_patterns(Path(fs.cwd))
    assert patterns == []


def test_load_gitignore_patterns_io_error(fs):
    fs.create_file(".gitignore")
    with patch("pathlib.Path.open", side_effect=IOError("Permission denied")):
        patterns = load_gitignore_patterns(Path(fs.cwd))
        assert patterns == []


def test_find_configured_files_symlink_and_overlap(fs):
    root = Path(fs.cwd)
    fs.create_file(root / "test.py")
    fs.create_symlink(root / "symlink.py", root / "target.py")
    lang_config1 = LanguageConfig(
        name="python",
        file_globs=["*.py"],
        prefix="#",
        check_encoding=True,
        template="# {path}",
    )
    lang_config2 = LanguageConfig(
        name="python-all",
        file_globs=["*.py"],
        prefix="#",
        check_encoding=True,
        template="# {path}",
    )
    files = list(find_configured_files(root, [lang_config1, lang_config2]))
    assert len(files) == 1
    assert files[0][0] == root / "test.py"
    assert files[0][1].name == "python"


def test_save_cache_io_error(fs):
    with patch("pathlib.Path.open", side_effect=IOError("Permission denied")):
        save_cache(Path(fs.cwd), {})


def test_load_cache_io_error(fs):
    fs.create_file(".autoheader_cache")
    with patch("pathlib.Path.open", side_effect=IOError("Permission denied")):
        cache = load_cache(Path(fs.cwd))
        assert cache == {}
