import json
from pathlib import Path

import pytest

cv2 = pytest.importorskip("cv2")

from mva.cli import main
from mva.video import contact_sheet, extract_frames, probe_video, video_id_for, write_manifest


@pytest.fixture
def sample_video(tmp_path):
    path = tmp_path / "sample.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10, (640, 480))
    if not writer.isOpened():
        pytest.skip("OpenCV não consegue criar vídeo mp4v neste ambiente")
    for i in range(50):
        frame = (255 * __import__("numpy").ones((480, 640, 3), dtype="uint8"))
        cv2.putText(frame, str(i), (40, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
        writer.write(frame)
    writer.release()
    return path


def test_probe_id_extract_and_outputs(sample_video, tmp_path):
    info = probe_video(sample_video)
    assert info.fps == pytest.approx(10, abs=0.1)
    assert info.duration_seconds == pytest.approx(5, abs=0.2)
    assert (info.width, info.height) == (640, 480)
    assert video_id_for(sample_video) == video_id_for(sample_video)
    frames = extract_frames(sample_video, tmp_path / "frames", every_seconds=1)
    assert len(frames) == 5
    assert [f.timestamp_seconds for f in frames] == pytest.approx([0, 1, 2, 3, 4])
    assert all(Path(f.path).exists() for f in frames)
    sheet = contact_sheet(frames, tmp_path / "contact_sheet.jpg")
    assert sheet.exists()
    manifest = write_manifest(info, frames, tmp_path)
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["video_id"] == video_id_for(sample_video)
    assert len(data["frames"]) == 5


def test_probe_errors(sample_video, tmp_path):
    with pytest.raises(ValueError, match="Extensão"):
        probe_video(tmp_path / "wrong.txt")
    with pytest.raises(ValueError, match="não encontrado"):
        probe_video(tmp_path / "missing.mp4")


def test_cli_probe_and_ingest(sample_video, tmp_path, capsys):
    assert main(["probe", str(sample_video)]) == 0
    probe = json.loads(capsys.readouterr().out)
    assert probe["video_id"].startswith("vid_")
    out = tmp_path / "cli_out"
    assert main(["ingest", str(sample_video), "--out", str(out), "--every", "1", "--width", "320"]) == 0
    assert (out / "frames").is_dir()
    assert (out / "contact_sheet.jpg").exists()
    assert json.loads((out / "manifest.json").read_text(encoding="utf-8"))["video_id"] == probe["video_id"]


def test_variable_frame_rate_uses_container_timestamps(tmp_path):
    import shutil, subprocess
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg indisponível")
    path = tmp_path / "vfr.mov"
    # Timestamps jump from ~3 s to 6 s: index/fps would place frames at the wrong time.
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc=duration=6:size=320x240:rate=30",
                    "-vf", "setpts='if(lt(T,3),PTS,PTS*2)'", "-vsync", "vfr", "-c:v", "libx264", str(path)], check=True)
    stamps = [f.timestamp_seconds for f in extract_frames(path, tmp_path / "f", every_seconds=1)]
    assert stamps[:4] == pytest.approx([0, 1, 2, 6], abs=0.05)
