"""S0.12 driver (11+). Usage:
 py pipe.py scan TAG URL MM:SS-MM:SS STEP     -> 144p/worst khuc, tile 1 khung/STEP s, xoa video quet
 py pipe.py seg TAG URL MM:SS-MM:SS            -> tai 720p doan
 py pipe.py proc TAG LANG LS LE [song]         -> analyze + motion(b) + listen [LS,LE] + tom tat; song=khong in loi
 py pipe.py listen TAG LANG LS LE [song]       -> chi listen them
"""
import sys, os, subprocess, json, glob, statistics, re
sys.stdout.reconfigure(encoding="utf-8")
from collections import Counter
S = os.path.dirname(os.path.abspath(__file__)); os.chdir(S)
FF = r"C:/Users/hongviet.doan/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.1-full_build/bin"
REPO = os.environ.get("REPO", r"D:/AI-Video-Pipeline")
FONT = r"C\:/Windows/Fonts/arial.ttf"
def sh(cmd, **k): return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **k)
def ydl(url, rng, out, fmt):
    r = sh(["py", "-m", "yt_dlp", "-q", "--no-playlist", "--ffmpeg-location", FF, "-f", fmt, "--download-sections", "*" + rng, "-o", out + ".%(ext)s", url])
    f = [x for x in glob.glob(out + ".*") if not x.endswith(".part")]
    return f[0] if f else None, r.stderr[-400:]
def dur(p): return float(sh(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]).stdout.strip() or 0)
cmd = sys.argv[1]; tag = sys.argv[2]
if cmd == "scan":
    url, rng, step = sys.argv[3], sys.argv[4], int(sys.argv[5])
    f, err = ydl(url, rng, tag + "_scan", "wv*/bv*[height<=240]/worst")
    if not f: print("ERR", err); sys.exit(1)
    d = dur(f); w = sh(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height","-of","csv=p=0",f]).stdout.strip()
    port = int(w.split(",")[1]) > int(w.split(",")[0])
    cw = "96:170" if port else "192:108"; cols = 12 if port else 8
    off = sum(int(x) * m for x, m in zip(rng.split("-")[0].split(":")[::-1], (1, 60, 3600)))
    n = int(d // step) + 1; rows = -(-n // cols)
    per = cols * (8 if port else 10)
    for k in range(0, n, per):
        out = f"{tag}_scan_{k//per+1}.jpg"
        sh(["ffmpeg", "-y", "-ss", str(k*step), "-i", f, "-vf", rf"fps=1/{step},scale={cw},drawtext=fontfile='{FONT}':text='%{{eif\:(t+{off+k*step})/60\:d}}m%{{eif\:mod(t+{off+k*step},60)\:d}}':x=2:y=2:fontsize=13:fontcolor=yellow:box=1:boxcolor=black@0.6,tile={cols}x{-(-min(per,n-k)//cols)}", "-frames:v", "1", out])
        print(out, os.path.exists(out))
    print("scan dur", d, "wh", w); os.remove(f)
elif cmd == "seg":
    url, rng = sys.argv[3], sys.argv[4]
    f, err = ydl(url, rng, tag, "bv*[height<=720]+ba/b[height<=720]")
    print(f, err if not f else "")
    if f:
        print(sh(["ffprobe","-v","error","-show_entries","stream=codec_type,start_time,width,height:format=duration","-of","compact",f]).stdout)
        bd = sh(["ffmpeg","-hide_banner","-i",f,"-t","20","-vf","blackdetect=d=0.3:pic_th=0.97","-an","-f","null","-"]).stderr
        print("black<20s:", re.findall(r"black_start:(\S+) black_end:(\S+)", bd))
elif cmd in ("proc", "listen"):
    lang, ls, le = sys.argv[3], float(sys.argv[4]), float(sys.argv[5]); song = len(sys.argv) > 6
    f = [x for x in glob.glob(tag + ".*") if x.split(".")[-1] in ("webm", "mp4", "mkv")][0]
    if cmd == "proc":
        r = sh(["py", "analyze.py", f, tag, os.environ.get("THR", "0.25")]); 
        if r.returncode: print(r.stderr[-800:])
        r = sh(["py", "motion_cv2b.py", f, tag + "_result.json"]); print("motion", r.stdout.strip(), r.stderr[-300:])
        d = json.load(open(tag + "_result.json", encoding="utf-8"))
        shots = d["shots"]; ds = [s["dur"] for s in shots]; mv = {m["i"]: m for m in d["motion_cv2"]}
        c = Counter(m["class"] for m in d["motion_cv2"]); n = len(shots)
        print(f"N={n} median={statistics.median(ds):.2f} min={min(ds)} max={max(ds)} per_min={n/(d['meta']['duration']/60):.1f} dur={d['meta']['duration']:.1f} wh={d['meta']['width']}x{d['meta']['height']}")
        print("motion%", {k: round(100*v/n) for k, v in c.items()})
        print("audio", d["audio_summary"], "n_sil", len(d["silences"]))
        print("sil", [(round(a,1), round(b,1)) for a, b in d["silences"]])
        ab = {"static":"S","pan_hoac_truck_hoac_tilt_hoac_pedestal":"T","zoom_in_hoac_dolly_in":"Zi","zoom_out_hoac_dolly_out":"Zo","roll":"R","khong_du_du_lieu":"?"}
        print("shots:", " ".join(f"{s['i']}:{s['start']:.1f}/{s['dur']:.1f}{ab[mv[s['i']]['class']]}" for s in shots))
        # one sheet with all mid frames
        fr = sorted(glob.glob(tag + "_frames/shot_*.jpg")); port = d["meta"]["height"] > d["meta"]["width"]
        cw, cols = ((90, 160), 12) if port else ((176, 99), 8)
        for part in range(0, len(fr), cols * (7 if port else 12)):
            sub = fr[part: part + cols * (7 if port else 12)]; out = f"{tag}_all_{part//(cols*(7 if port else 12))+1}.jpg"
            lst = tag + "_lst.txt"; open(lst, "w").write("".join(f"file '{os.path.abspath(x)}'\n" for x in sub))
            rows = -(-len(sub) // cols)
            sh(["ffmpeg","-y","-f","concat","-safe","0","-i",lst,"-vf",f"scale={cw[0]}:{cw[1]},drawtext=fontfile='{FONT}':text='%{{n}}':start_number={part+1}:x=2:y=2:fontsize=14:fontcolor=yellow:box=1:boxcolor=black@0.7,tile={cols}x{rows}","-frames:v","1",out])
            print(out)
    out = f"{tag}_L{int(ls)}"
    if not os.path.exists(out + "/listen.json"): r = sh(["py", REPO + "/tools/audio_listen.py", os.path.abspath(f), "--start", str(ls), "--end", str(le), "--out", os.path.abspath(out), "--lang", lang], cwd=REPO)
    if not os.path.exists(out + "/listen.json"): print("LISTEN ERR", r.stderr[-800:]); sys.exit()
    L = json.load(open(out + "/listen.json", encoding="utf-8"))
    print(f"LISTEN {ls}-{le} share={L['music_share']} music={L.get('music')}")
    print("mdb(2s):", " ".join(f"{int(ls+i)}:{v:.0f}" for i, v in enumerate(L["music_db"]) if i % 2 == 0))
    print("vdb(2s):", " ".join(f"{int(ls+i)}:{v:.0f}" for i, v in enumerate(L["voice_db"]) if i % 2 == 0))
    print("events:", "; ".join(f"{ls+e['t']:.0f} {e['what']} {e['db']}" for e in L["music_events"]))
    skip = {"Speech","Music","Sound effect","Musical instrument","Inside, small room","Silence","Narration, monologue","Male speech, man speaking","Female speech, woman speaking","Conversation"}
    print("tags:", "; ".join(f"{ls+t['t']:.0f} " + ",".join(f"{a} {b:.2f}" for a, b in t["top"] if a not in skip and b >= 0.12) + ("|" + ",".join(str(m) for m in t["mood"]) if t.get("mood") else "") for t in L["tags"] if any(a not in skip and b >= 0.12 for a, b in t["top"]) or t.get("mood")))
    for l in L.get("lines", []):
        print(f"  {ls+l['start']:.1f}-{ls+l['end']:.1f}" + ("" if song else " " + l["text"][:60]))
    L.pop("lines", None); json.dump(L, open(f"{tag}_L{int(ls)}_numbers.json", "w", encoding="utf-8"), ensure_ascii=False)
