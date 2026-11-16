import os

from deepin_jumplist.recent import load_recent, parse_timestamp, parse_xbel, uri_to_path

XBEL = """<?xml version="1.0" encoding="UTF-8"?>
<xbel version="1.0"
      xmlns:bookmark="http://www.freedesktop.org/standards/desktop-bookmarks"
      xmlns:mime="http://www.freedesktop.org/standards/shared-mime-info">
  <bookmark href="file://{d}/old.txt" added="2024-01-01T10:00:00Z" modified="2024-01-01T10:00:00Z" visited="2024-01-01T10:00:00Z">
    <info><metadata owner="http://freedesktop.org"><mime:mime-type type="text/plain"/></metadata></info>
  </bookmark>
  <bookmark href="file://{d}/My%20Photo.jpg" added="2024-03-01T10:00:00.123456789Z" modified="2024-03-01T10:00:00Z" visited="2024-03-02T10:00:00Z">
    <info><metadata owner="http://freedesktop.org"><mime:mime-type type="image/jpeg"/></metadata></info>
  </bookmark>
  <bookmark href="file://{d}/report.pdf" added="2024-02-01T10:00:00Z" modified="2024-02-01T10:00:00Z" visited="2024-02-01T10:00:00Z"/>
  <bookmark href="file://{d}/gone.odt" added="2024-04-01T10:00:00Z"/>
  <bookmark href="https://example.com/page" added="2024-05-01T10:00:00Z"/>
  <bookmark href="file://{d}/folder" added="2024-02-15T10:00:00Z"/>
</xbel>
"""


def make(tmp_path):
    for name in ("old.txt", "My Photo.jpg", "report.pdf"):
        (tmp_path / name).write_text("x")
    (tmp_path / "folder").mkdir()
    xbel = tmp_path / "recently-used.xbel"
    xbel.write_text(XBEL.format(d=tmp_path))
    return str(xbel)


def test_parse_orders_newest_first_and_skips_remote(tmp_path):
    items = parse_xbel(make(tmp_path))
    names = [os.path.basename(i.path) for i in items]
    assert names == ["gone.odt", "My Photo.jpg", "folder", "report.pdf", "old.txt"]
    assert items[1].mime_type == "image/jpeg"


def test_load_recent_filters_missing_limit_and_folders(tmp_path):
    xbel = make(tmp_path)
    names = [i.name for i in load_recent(10, xbel_path=xbel)]
    assert names == ["My Photo.jpg", "report.pdf", "old.txt"]
    assert [i.name for i in load_recent(2, xbel_path=xbel)] == ["My Photo.jpg", "report.pdf"]
    with_dirs = [i.name for i in load_recent(10, include_folders=True, xbel_path=xbel)]
    assert with_dirs == ["My Photo.jpg", "folder", "report.pdf", "old.txt"]


def test_exclude_and_hidden(tmp_path):
    xbel = make(tmp_path)
    photo = str(tmp_path / "My Photo.jpg")
    pdf = str(tmp_path / "report.pdf")
    pdf_ts = parse_timestamp("2024-02-01T10:00:00Z")
    names = [i.name for i in load_recent(10, exclude=[photo], hidden={pdf: pdf_ts}, xbel_path=xbel)]
    assert names == ["old.txt"]
    # Opened again after being hidden -> it comes back.
    names = [i.name for i in load_recent(10, hidden={pdf: pdf_ts - 1}, xbel_path=xbel)]
    assert "report.pdf" in names


def test_bad_input():
    assert parse_xbel("/nonexistent/file.xbel") == []
    assert parse_timestamp("garbage") == 0.0
    assert parse_timestamp(None) == 0.0
    assert uri_to_path("file://otherhost/x") is None
    assert uri_to_path("file:///a%20b") == "/a b"


def test_recent_folders_from_files_and_folder_entries(tmp_path):
    from deepin_jumplist.recent import load_recent_folders

    xbel = make(tmp_path)
    sub = tmp_path / "Photos"
    sub.mkdir()
    (sub / "beach.png").write_text("x")
    extra = tmp_path / "extra.xbel"
    extra.write_text(
        open(xbel).read().replace(
            "</xbel>",
            f'<bookmark href="file://{sub}/beach.png" added="2024-06-01T10:00:00Z"/></xbel>',
        )
    )
    folders = load_recent_folders(10, xbel_path=str(extra))
    # Newest first; a folder appears once even if several files in it were used.
    assert [f.path for f in folders] == [str(sub), str(tmp_path), str(tmp_path / "folder")]
    assert all(f.mime_type == "inode/directory" for f in folders)
    assert len(load_recent_folders(1, xbel_path=str(extra))) == 1


def test_recent_folders_respect_pins_and_hidden(tmp_path):
    from deepin_jumplist.recent import load_recent_folders

    xbel = make(tmp_path)
    folders = load_recent_folders(10, exclude=[str(tmp_path)], xbel_path=xbel)
    assert [f.path for f in folders] == [str(tmp_path / "folder")]
    newest = parse_timestamp("2024-03-02T10:00:00Z")
    folders = load_recent_folders(10, hidden={str(tmp_path): newest}, xbel_path=xbel)
    assert str(tmp_path) not in [f.path for f in folders]


def test_files_list_never_contains_folders(tmp_path):
    xbel = make(tmp_path)
    assert all(os.path.isfile(i.path) for i in load_recent(10, xbel_path=xbel))
