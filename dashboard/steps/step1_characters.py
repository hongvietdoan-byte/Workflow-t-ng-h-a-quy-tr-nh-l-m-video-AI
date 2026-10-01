"""Step 1 · 1e: Character Bible — reference pictures, outfits, subjects, voices, Lock, anchors (split from step1.py, S9.5)."""
from dashboard.common import *  # noqa: F401,F403  (shared imports + helpers)
from dashboard import common as C
from dashboard.steps.step1_v2 import cap, say, is_next  # noqa: F401  (v2: long captions / notes become a one-line summary + ⓘ)


def character_reference_panel(p: Pipeline, pid: int, chars) -> None:
    """Character Bible: the reference picture(s) of each character, visible here and changeable (this is what image generation copies)."""
    linked = assets.link_characters(p.conn, pid, [c["name"] for c in chars])
    pool = [a for a in assets.project_assets(p.conn, pid) if a["kind"] in ("character", "pet") and a["images"]]
    saved = {r["name"]: r for r in p.conn.execute("SELECT name, ref_asset_id, ref_image_id, ref_image_ids FROM characters WHERE project_id=?", (pid,))}
    have = sum(1 for a in linked.values() if a)
    with st.expander(f"🖼 Ảnh tham chiếu của từng nhân vật — {have}/{len(chars)} đã có", expanded=is_next("refs", have < len(chars) or not pool)):   # v2: the label carries the count
        cap("Đây là (những) ảnh mà bước gen ảnh sẽ **bám theo** (gương mặt, tóc, trang phục). Mặc định tự chọn theo tên, ưu tiên ảnh MỘT người rõ mặt "
                   "(không phải cả tấm bảng nhiều tư thế) và lấy thêm góc/chi tiết thứ hai nếu có, để nhân vật không bị lẫn với người khác trong cảnh. "
                   "Bạn đổi được sang tài nguyên khác, hoặc tự chọn 1-2 ảnh cụ thể. Muốn thêm tài nguyên, chọn ở mục “🧰 Tài nguyên đi kèm kịch bản” phía trên.")
        if not pool:
            say("warning", "Dự án chưa chọn tài nguyên nhân vật nào, nên ảnh sẽ vẽ chỉ theo mô tả chữ (dễ lệch thiết kế). Chọn ở “🧰 Tài nguyên đi kèm kịch bản”.",
                f"script-noasset-{pid}", "Chưa chọn tài nguyên nhân vật — ảnh vẽ theo mô tả chữ")
        options = ["auto", "none"] + [a["id"] for a in pool]
        labels = {"auto": "Tự động (theo tên)", "none": "Không dùng ảnh (vẽ theo mô tả)", **{a["id"]: f"{a['name']} ({len(a['images'])} ảnh)" for a in pool}}
        for c in chars:
            row = saved.get(c["name"])
            a = linked[c["name"]]
            with st.container(border=True):
                left, right = st.columns([1.1, 3], vertical_alignment="top")
                if a:
                    left.image([assets.thumbnail(img["path"], 220) for img in a["refs"]], width=105)
                else:
                    left.caption("— chưa có ảnh")
                right.markdown(f"**{escape(c['name'])}** — " + (f"dùng {len(a['refs'])} ảnh của **{escape(a['name'])}**" if a else "vẽ theo mô tả chữ"))
                mode = "auto" if row["ref_asset_id"] is None else ("none" if row["ref_asset_id"] == 0 else row["ref_asset_id"])
                if mode not in options:
                    mode = "auto"
                pick = right.selectbox("Ảnh tham chiếu lấy từ", options, options.index(mode), format_func=lambda o: labels[o], key=f"cref_{pid}_{c['name']}")
                new_asset = None if pick == "auto" else (0 if pick == "none" else pick)
                if pick != mode:                                     # another source picked: save it (automatic picture choice until chosen otherwise)
                    assets.set_character_link(p.conn, pid, c["name"], new_asset, None, None)
                    _anchor_reset(p, pid, c["name"])
                    st.rerun()
                shown = a if pick == "auto" else next((x for x in pool if x["id"] == pick), None)
                if shown and len(shown["images"]) > 1:
                    numbers = list(range(1, len(shown["images"]) + 1))
                    current_ids = {img["id"] for img in a["refs"]} if a and a["id"] == shown["id"] else set()
                    default = [i for i, img in enumerate(shown["images"], 1) if img["id"] in current_ids] or [1]
                    chosen_nums = right.multiselect("Dùng ảnh số (chọn 1-2 ảnh rõ mặt, nhiều góc/chi tiết thì càng chuẩn)", numbers, default,
                                                    key=f"cimg_{pid}_{c['name']}")
                    right.image([assets.thumbnail(img["path"], 160) for img in shown["images"]], width=70, caption=[str(i) for i in numbers])
                    if chosen_nums and set(chosen_nums) != set(default):
                        ids = [shown["images"][i - 1]["id"] for i in sorted(chosen_nums)]
                        assets.set_character_link(p.conn, pid, c["name"], shown["id"], ids[0], ids)
                        _anchor_reset(p, pid, c["name"])
                        st.rerun()
                outfit_panel(p, pid, c["name"], right)


def outfit_panel(p: Pipeline, pid: int, name: str, box) -> None:
    """A different outfit for this video, from pictures + text: pick outfit picture(s) from the library (another skin, a costume photo),
    optionally generate a 2-picture character set wearing it (it then becomes the reference; nothing to approve)."""
    current = assets.outfit_images(p.conn, pid, name)
    with box.popover("👗 Trang phục cho video này" + (f" — đang dùng {len(current)} ảnh" if current else ""), width="stretch"):
        cap("Muốn nhân vật mặc trang phục khác (skin khác, đồ theo kịch bản): chọn ảnh trang phục trong kho. Khi gen, mặt/tóc lấy từ ảnh "
                   "nhân vật, quần áo lấy từ ảnh trang phục. Mô tả thêm bằng chữ ở ô “Trang phục / dấu hiệu” (mục ✏ Sửa nhân vật).")
        pool = [a for a in assets.project_assets(p.conn, pid) if a["images"]]
        by_id = {img["id"]: (a, n) for a in pool for n, img in enumerate(a["images"], 1)}
        chosen = st.multiselect("Ảnh trang phục", list(by_id), [i["id"] for i in current if i["id"] in by_id],
                                format_func=lambda i: f"{by_id[i][0]['name']} · ảnh {by_id[i][1]}", key=f"outfit_{pid}_{name}",
                                max_selections=2)
        if chosen:
            st.image([assets.thumbnail(by_id[i][0]["images"][by_id[i][1] - 1]["path"], 160) for i in chosen], width=70)
        if [i["id"] for i in current] != chosen and st.button("💾 Lưu trang phục", key=f"outfit_save_{pid}_{name}"):
            assets.set_outfit(p.conn, pid, name, chosen)
            st.rerun()
        runner = image_runner(p) if current else None
        if current and st.button("🧍 Tạo bộ ảnh nhân vật mặc trang phục này (2 ảnh Deepix)", key=f"outfit_set_{pid}_{name}",
                                 disabled=runner is None, help="Chính diện + góc 3/4, toàn thân. Tạo xong tự thành ảnh tham chiếu của nhân vật "
                                                               "trong dự án này, mọi cảnh bám theo cùng một bộ; đổi lại được ở ô “Ảnh tham chiếu lấy từ”."):
            with st.spinner("Deepix đang vẽ bộ ảnh nhân vật (khoảng 1 phút)…"):
                if act(lambda: costume.make_character_set(p, pid, name, runner.provider, C.DATA), f"Đã tạo bộ ảnh cho {name}"):
                    st.rerun()


def subject_panel(p: Pipeline, pid: int, chars) -> None:
    """Seedance Subject Library: upload each character once, then attach it to Seedance videos."""
    proj = p.project(pid)
    rows = p.conn.execute("SELECT name, subject_asset_id, subject_status, subject_name FROM characters"
                          " WHERE project_id=?", (pid,)).fetchall()
    active = sum(1 for r in rows if r["subject_status"] == "active")
    with st.expander(f"🧩 Kho chủ thể Seedance — {active}/{len(rows)} nhân vật đã có"):
        catalog = subjects.games()
        keys = list(catalog)
        game = st.selectbox("Game / loại nội dung của dự án", keys,
                            index=keys.index(proj["game"]) if proj["game"] in keys else 0,
                            format_func=lambda k: catalog[k][0], key=f"game_{pid}")
        if game != proj["game"]:
            p.set_game(pid, game)
        if subjects.is_covered(game):
            say("success", "Free Fire đã ký thỏa thuận bản quyền với Clip AI: chủ thể ở trạng thái active đã qua duyệt "
                "người thật + bản quyền, dùng được trong Seedance.", f"script-subj-cover-{pid}", "Đã có thỏa thuận bản quyền với Clip AI")
        else:
            say("warning", "Game / nội dung này chưa có thỏa thuận bản quyền: chủ thể active chỉ qua duyệt người thật; "
                "khi gen vẫn có thể bị chặn bản quyền.", f"script-subj-nocover-{pid}", "Chưa có thỏa thuận bản quyền cho nội dung này")
        with st.expander("➕ Thêm game / loại nội dung khác"):
            g_key = st.text_input("Mã ngắn (vd AOV, MV_CA_SI)", key=f"gnew_key_{pid}")
            g_label = st.text_input("Tên hiển thị", key=f"gnew_label_{pid}")
            g_cov = st.checkbox("Đã ký thỏa thuận bản quyền với Clip AI", False, key=f"gnew_cov_{pid}",
                                help="Chỉ tick khi thật sự có thỏa thuận; ảnh hưởng thông báo hiển thị.")
            if st.button("Thêm", key=f"gnew_{pid}", disabled=not (g_key.strip() and g_label.strip())):
                if act(lambda: subjects.add_game(g_key, g_label, g_cov), "Đã thêm"):
                    st.rerun()
        st.dataframe([{"Nhân vật": r["name"], "Trạng thái": subjects.STATUS_LABEL.get(r["subject_status"], r["subject_status"]),
                       "Tên trên kho": r["subject_name"] or ""} for r in rows], width="stretch", hide_index=True,
                     height=min(38 * (len(rows) + 1) + 3, 200))
        try:
            library = factory.subject_library()
        except ProviderError as e:
            st.error(f"Clip AI: {e}")
            return
        if library is None:
            cap("Cần CLIPAI_TOKEN và VIDEO_PROVIDER=clipai (hoặc SUBJECT_PROVIDER=mock để thử) để tải lên kho.")
            return
        who = st.selectbox("Nhân vật", [r["name"] for r in rows], key=f"subj_who_{pid}")
        up = st.file_uploader("Ảnh nhân vật (JPG / PNG / WebP)", type=["jpg", "jpeg", "png", "webp"],
                              key=f"subj_up_{pid}_{who}")
        default_name = f"{game}_{who}".replace(" ", "_")  # any name is fine; the prefix just keeps the library tidy
        name = st.text_input("Tên trên kho", default_name, key=f"subj_name_{pid}_{who}")
        b1, b2, b3 = st.columns(3)
        if b1.button("⬆ Tải lên kho chủ thể", disabled=up is None, key=f"subj_go_{pid}", type="primary"):
            suffix = os.path.splitext(up.name)[1] or ".png"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                f.write(up.getvalue())
            try:
                with st.spinner("Đang tải lên và chờ kho duyệt (có thể mất 1–3 phút)…"):
                    ok = act(lambda: subjects.link(p, pid, who, library.upload(f.name, name)), f"Đã có chủ thể cho {who}")
            finally:
                os.remove(f.name)
            if ok:
                st.rerun()
        if b2.button("⟳ Cập nhật trạng thái", key=f"subj_refresh_{pid}"):
            act(lambda: st.toast(f"{subjects.refresh(p, pid, library)} chủ thể vừa active"))
            st.rerun()
        if b3.button("Gỡ liên kết", key=f"subj_unlink_{pid}", help="Chỉ bỏ liên kết trong dự án; ảnh vẫn ở kho Clip AI"):
            subjects.unlink(p, pid, who)
            st.rerun()
        with st.expander("📥 Nhập chủ thể đã có trên kho"):
            try:
                assets = [a for a in library.list_assets("image") if a.get("asset_id")]
            except ProviderError as e:
                st.error(str(e))
                assets = []
            if not assets:
                cap("Kho chưa có ảnh nào (hoặc không đọc được).")
            else:
                pick = st.selectbox("Chủ thể trên kho", assets, key=f"subj_pick_{pid}",
                                    format_func=lambda a: f"{a.get('name')} · {a.get('provider_status')}")
                if st.button(f"Gắn cho {who}", key=f"subj_link_{pid}"):
                    act(lambda: subjects.link(p, pid, who, pick), f"Đã gắn cho {who}")
                    st.rerun()


def _voices(pid: int):
    key = f"voices_{pid}"
    if key not in st.session_state:
        try:
            provider = music.audio_provider()
            st.session_state[key] = voice.library(provider) if provider else []   # official + team voices (FF 'VN' clones first)
        except ProviderError as e:
            st.session_state[key] = []
            cap(f"Không lấy được danh sách giọng: {e}")
    return st.session_state[key]


def voice_preview_row(p: Pipeline, pid: int, name: str, voice_id, voice_name) -> None:
    """🔈 Vietnamese sample sentence in the chosen voice (one short TTS — a little audio credit), to hear accent and tones."""
    if not voice_id:
        return
    directory = voice.previews_dir(C.DATA, pid)
    mine = [e for e in audio_lib.load(directory) if e.get("preview_for") == name and e.get("voice_id") == voice_id]
    b1, b2 = st.columns([1.4, 3], vertical_alignment="center")
    if b1.button("🔈 Nghe thử câu mẫu tiếng Việt", key=f"vprev_{pid}_{name}", help="Tạo 1 câu mẫu bằng giọng này (tốn một chút credit âm thanh)."):
        try:
            provider = music.audio_provider()
        except ProviderError as e:
            st.error(str(e))
            provider = None
        if provider is not None:
            voice.preview(provider, C.DATA, pid, voice_id, voice_name or "", name, ledger=(p.conn, pid))
            st.rerun()
    if mine:
        e = mine[-1]
        if e["state"] == "running":
            try:
                provider = music.audio_provider()
                if provider is not None:
                    audio_lib.refresh(provider, directory)
                    e = [x for x in audio_lib.load(directory) if x.get("preview_for") == name and x.get("voice_id") == voice_id][-1]
            except ProviderError:
                pass
        if e["state"] == "succeeded" and e.get("file"):
            b2.audio(os.path.join(directory, e["file"]))
        else:
            b2.caption(ui.state_label(e["state"], "audio") + (" — bấm lại sau vài giây" if e["state"] == "running" else ""))


def character_detail_panel(p: Pipeline, pid: int, c, voices, client, locked: bool, has_ref: bool = True) -> None:
    """Character Lock + voice + anchor of one character (skills: consistency designer, narration-writer)."""
    lock = claude_tasks.get_lock(c)
    prof = voice.get_profile(c)
    head = f"**{escape(c['name'])}** — " + ("🔒 Lock ✓" if lock else "🔒 chưa có Lock") + " · " \
           + (f"🎙 {escape(prof.get('voice_name') or str(prof.get('voice_id')))}" if prof.get("voice_id") else "🎙 chưa có giọng") \
           + " · " + ("🖼 ảnh mốc đã duyệt" if c["anchor_approved"] else "🖼 ảnh mốc chưa duyệt")
    with st.expander(head.replace("**", ""), expanded=False):
        st.markdown("**🔒 Character Lock** — điều không được lệch ở mọi cảnh (dùng cho prompt ảnh, QC ảnh, QC video)")
        k = f"lock_{pid}_{c['name']}"
        must = st.text_area("Bắt buộc giữ", lock.get("must_keep", ""), key=f"{k}_must", height=60, disabled=locked)
        may = st.text_input("Được đổi giữa các cảnh", lock.get("may_change", ""), key=f"{k}_may", disabled=locked)
        forb = st.text_area("Cấm lệch", lock.get("forbidden", ""), key=f"{k}_forb", height=60, disabled=locked)
        b1, b2 = st.columns(2)
        if b1.button("💾 Lưu Lock", key=f"{k}_save", disabled=locked):
            act(lambda: claude_tasks.set_lock(p, pid, c["name"], {"must_keep": must, "may_change": may, "forbidden": forb}), "Đã lưu")
            st.rerun()
        if b2.button("🤖 Claude viết Lock từ ảnh", key=f"{k}_ai", disabled=locked or client is None, help=None if client else claude_hint()):
            with st.spinner("Claude đang xem ảnh tham chiếu…"):
                if act(lambda: claude_tasks.character_lock(p, pid, c["name"], client), "Đã viết Character Lock"):
                    for suffix in ("must", "may", "forb"):
                        st.session_state.pop(f"{k}_{suffix}", None)
                    st.rerun()
        st.markdown("**🎙 Giọng nói (TTS)** — thoại tiếng Việt được đọc bằng giọng này (Bước 3)")
        if voices:
            ordered = voice.vietnamese_first(voices)          # v3: voices that list Vietnamese first (🇻🇳)
            ids = [None] + [v.get("id") for v in ordered]
            label = lambda v: ("⭐ " if voice.preferred(v) else "🇻🇳 " if voice.speaks_vi(v) else "") + voice.display_name(v) + (  # noqa: E731
                f" · {'nam' if voice.voice_gender(v) == 'male' else 'nữ'}" if voice.preferred(v) else "")
            names = {v.get("id"): label(v) for v in ordered}
            names.update({v.get("id"): label(v) for v in voices if v.get("id") not in names})
            cur = prof.get("voice_id") if prof.get("voice_id") in ids else None
            v1, v2 = st.columns([2, 3])
            pick = v1.selectbox("Giọng", ids, index=ids.index(cur), key=f"voice_{pid}_{c['name']}",
                                format_func=lambda i: "— chưa chọn —" if i is None else f"{names.get(i)} (#{i})")
            persona = v2.text_input("Cách nói (persona)", prof.get("persona", ""), key=f"persona_{pid}_{c['name']}",
                                    placeholder="câu ngắn, hay cà khịa, nói 'nha'…")
            if (pick, persona) != (cur, prof.get("persona", "")) and st.button("💾 Lưu giọng", key=f"voice_save_{pid}_{c['name']}"):
                voice.set_profile(p.conn, pid, c["name"], {"voice_id": pick, "voice_name": names.get(pick), "persona": persona} if pick else None)
                st.rerun()
            voice_preview_row(p, pid, c["name"], cur, names.get(cur))
        else:
            cap("Chưa có danh sách giọng (cần AUDIO_PROVIDER / Clip AI). Voice Design / Voice Clone chỉ có trên web ClipAI: tạo ở đó rồi chọn ở đây.")
        st.markdown("**🖼 Ảnh mốc** — ảnh tham chiếu bạn xác nhận là ĐÚNG nhân vật trước khi gen cả loạt")
        if c["anchor_approved"]:
            if st.button("↩ Bỏ duyệt ảnh mốc", key=f"anchor_off_{pid}_{c['name']}"):
                p.conn.execute("UPDATE characters SET anchor_approved=0 WHERE project_id=? AND name=?", (pid, c["name"]))
                p.conn.commit()
                st.rerun()
        elif not has_ref:
            cap("Chưa có ảnh tham chiếu: nhân vật đang vẽ theo mô tả chữ (dễ lệch giữa các cảnh). Chọn tài nguyên ở "
                       "“🧰 Tài nguyên đi kèm kịch bản” hoặc tạo bộ ảnh ở “👗 Trang phục cho video này”, rồi duyệt ảnh mốc.")
            if st.button("Vẫn vẽ theo mô tả chữ — bỏ qua ảnh mốc", key=f"anchor_on_{pid}_{c['name']}"):
                p.conn.execute("UPDATE characters SET anchor_approved=1 WHERE project_id=? AND name=?", (pid, c["name"]))
                p.conn.commit()
                st.rerun()
        elif st.button("✔ Ảnh tham chiếu ở trên là đúng — duyệt ảnh mốc", key=f"anchor_on_{pid}_{c['name']}"):
            p.conn.execute("UPDATE characters SET anchor_approved=1 WHERE project_id=? AND name=?", (pid, c["name"]))
            p.conn.commit()
            st.rerun()


def bible_check_box(p: Pipeline, pid: int, rows, client, locked: bool) -> None:
    """F1: the Bible text against the library pictures — mismatches shown with Claude's suggested wording, one click to use it."""
    flags = claude_tasks.bible_flags(p, pid)
    for r in rows:
        if r["name"] not in flags:
            continue
        res = json.loads(r["bible_check"] or "{}")
        box = st.container(border=True)
        with box:
            say("warning", f"⚑ **{r['name']}**: mô tả mâu thuẫn với ảnh tài nguyên — " + "; ".join(flags[r["name"]]), f"script-bflag-{pid}-{r['name']}",
                f"⚑ {r['name']}: mô tả mâu thuẫn với ảnh tài nguyên")
        fixed = (res.get("fixed_description") or "").strip()
        if fixed:
            with box:
                cap(f"Đề xuất: {fixed}", f"script-bfix-{pid}-{r['name']}")
            if not locked and box.button("✔ Dùng đề xuất này", key=f"bfix_{pid}_{r['name']}"):
                act(lambda: llm_io.update_character(p, pid, r["name"], fixed, r["wardrobe"]), "Đã sửa mô tả theo ảnh")
                st.rerun()
    if client is not None and st.button("🔍 Kiểm mô tả nhân vật với ảnh tài nguyên (1 lượt Claude, chỉ nhân vật đổi từ lần kiểm trước)",
                                        key=f"bcheck_{pid}"):
        with st.spinner("Claude đang so mô tả với ảnh…"):
            act(lambda: claude_tasks.bible_check(p, pid, client), "Đã kiểm xong")
        st.rerun()


def _bible_summary(rows, locked: bool) -> str:
    n = len(rows)
    anchors = sum(1 for r in rows if r["anchor_approved"])
    voiced = sum(1 for r in rows if voice.get_profile(r).get("voice_id"))
    return f"👥 {n} mục" + (" · 🔒 đã khóa" if locked else " · chưa khóa") + f" · ảnh mốc {anchors}/{n} · giọng {voiced}/{n}"


def character_bible_panel(p: Pipeline, pid: int, chars, risky) -> None:
    char_names = [c["name"] for c in chars]
    locked = any(c["locked"] for c in chars)
    rows = p.conn.execute("SELECT * FROM characters WHERE project_id=?", (pid,)).fetchall()
    with ui.fold("1e · 👥 Character Bible", _bible_summary(rows, locked), f"bible_{pid}",
                 default_open=is_next("bible", not locked or any(not r["anchor_approved"] for r in rows))) as bible_open:  # E1.15
        if bible_open:
            if ui.v2_on():           # v2: the fold title above already says "1e · Character Bible" and the counts (P4: no second heading)
                if risky:
                    st.caption(f"⚠ {len(risky)} mục có thể vướng IP (xem “⚠ Rủi ro” ở góc trên)")
            else:
                head, status = st.columns([3, 2], vertical_alignment="center")
                head.markdown(ui.card_title("1e · 👥 Character Bible", f"{len(chars)} mục" + (" · 🔒 đã khóa" if locked else "")), unsafe_allow_html=True)
                if risky:
                    status.caption(f"⚠ {len(risky)} mục có thể vướng IP (xem “⚠ Rủi ro” ở góc trên)")
            linked = assets.link_characters(p.conn, pid, char_names)
            bible_rows = ([{"Nhân vật / đối tượng": r["name"],
                           "Mô tả": r["description"] + (f" · {r['wardrobe']}" if r["wardrobe"] else ""),
                           "Ảnh tham chiếu": (f"✔ {linked[r['name']]['name']} · {len(linked[r['name']]['refs'])} ảnh" if linked.get(r["name"]) else "— vẽ theo mô tả"),
                           "Lock": "✔" if r["lock_rules"] else "—",
                           "Giọng": voice.get_profile(r).get("voice_name") or ("—" if not voice.get_profile(r).get("voice_id") else "✔"),
                           "Ảnh mốc": "✔" if r["anchor_approved"] else "—",
                           "IP": "⚠" if r["name"] in risky else "",
                           } for r in rows])
            if ui.v2_on():                         # v2: a table that follows light/dark; long descriptions clipped (full text: ✏ Sửa / thêm below)
                from dashboard.design import components as D
                def clip(t: str) -> "D.Raw":
                    return D.Raw(f'<span title="{escape(t)}">{escape(t if len(t) <= 70 else t[:69].rstrip() + "…")}</span>')
                heads = list(bible_rows[0]) if bible_rows else []
                st.html(D.table(heads, [[clip(v) if h == "Mô tả" else v for h, v in row.items()] for row in bible_rows]))
            else:
                st.dataframe(bible_rows, width="stretch", hide_index=True, height=min(38 * (len(rows) + 1) + 3, 260))
            client = llm_client()
            bible_check_box(p, pid, rows, client, locked)
            character_reference_panel(p, pid, chars)
            voices = _voices(pid)
            st.markdown("**🔒 Lock · 🎙 Giọng · 🖼 Ảnh mốc của từng nhân vật**")
            speakers = {ln["speaker"].upper() for ln in voice.planned_lines(p.conn, pid) if ln["speaker"]}
            no_voice = [r["name"] for r in rows if r["name"].upper() in speakers and not voice.get_profile(r).get("voice_id")]
            vi_pool = [v for v in voice.vietnamese_first(voices) if voice.speaks_vi(v)] if voices else []
            if voices:
                n_f = sum(1 for v in vi_pool if voice.voice_gender(v) == "female")
                n_pref = sum(1 for v in vi_pool if voice.preferred(v))
                cap(f"🇻🇳 {len(vi_pool)} giọng tiếng Việt ({n_f} nữ)"
                           + (f", ưu tiên ⭐ {n_pref} giọng clone Việt của team (hậu tố VN, `data/voices_vi.json`)" if n_pref else
                              " — chưa thấy giọng clone Việt của team (⭐): kiểm tra nhóm FF ở AI Audio → Voice Actors")
                           + ". Nên nghe thử câu mẫu. Từ tiếng Anh/tên riêng được đọc theo `data/pronunciation_vi.json`."
                           + (f" ⚠ {len(speakers)} nhân vật có thoại nhưng chỉ {len(vi_pool)} giọng tiếng Việt: sẽ phải dùng chung giọng." if 0 < len(vi_pool) < len(speakers) else ""))
            if no_voice and voices and client is not None:
                if st.button(f"🤖 Claude chọn giọng cho {len(no_voice)} nhân vật có thoại", key=f"cast_{pid}"):
                    with st.spinner("Claude đang chọn giọng…"):
                        act(lambda: claude_tasks.cast_voices(p, pid, client, voices), "Đã chọn giọng")
                    for r in rows:                     # the voice pickers must show the new choice, not their old widget value
                        st.session_state.pop(f"voice_{pid}_{r['name']}", None)
                        st.session_state.pop(f"persona_{pid}_{r['name']}", None)
                    st.rerun()
            for r in rows:
                character_detail_panel(p, pid, r, voices, client, locked, has_ref=bool(linked.get(r["name"])))
            if subjects_visible(p, pid):
                subject_panel(p, pid, chars)
            with st.expander("✏ Sửa / thêm nhân vật, đối tượng · khóa"):
                if locked:
                    cap("Character Bible đang khóa. Muốn sửa phải mở khóa (ảnh đã gen sẽ báo ⚠ cũ nếu mô tả đổi).")
                    if st.button("🔓 Mở khóa để sửa", key="btn_bad_unlock"):
                        act(lambda: llm_io.unlock_character_bible(p, pid), "Đã mở khóa Character Bible")
                        st.rerun()
                else:
                    who = st.selectbox("Chọn mục cần sửa", char_names, key=f"csel_{pid}")
                    c = next(c for c in chars if c["name"] == who)
                    n_name = st.text_input("Tên", c["name"], key=f"cn_{pid}_{c['name']}")
                    n_desc = st.text_area("Mô tả", c["description"], key=f"cd_{pid}_{c['name']}", height=80)
                    n_ward = st.text_input("Trang phục / dấu hiệu", c["wardrobe"] or "", key=f"cw_{pid}_{c['name']}")
                    if st.button("Lưu", key=f"cs_{pid}_{c['name']}"):
                        if act(lambda: llm_io.update_character(p, pid, c["name"], n_desc, n_ward, n_name), f"Đã lưu {n_name}"):
                            st.rerun()
                st.markdown("**➕ Thêm nhân vật / đối tượng**")
                cap("Không chỉ người: cũng có thể là sinh vật, linh vật, đạo cụ… bất cứ thứ gì cần giống nhau ở mọi cảnh.")
                a_name = st.text_input("Tên", key=f"cadd_name_{pid}")
                a_desc = st.text_area("Mô tả ngoại hình", key=f"cadd_desc_{pid}", height=70)
                a_ward = st.text_input("Trang phục / dấu hiệu (tùy chọn)", key=f"cadd_ward_{pid}")
                if st.button("Thêm vào Character Bible", key=f"cadd_{pid}", disabled=not (a_name.strip() and a_desc.strip())):
                    if act(lambda: llm_io.add_character(p, pid, a_name, a_desc, a_ward), f"Đã thêm {a_name}"):
                        st.rerun()


def _anchor_reset(p: Pipeline, pid: int, name: str) -> None:
    """Other reference pictures chosen: the approved anchor no longer applies."""
    p.conn.execute("UPDATE characters SET anchor_approved=0 WHERE project_id=? AND name=?", (pid, name))
    p.conn.commit()


# siblings (bottom import: the parts use each other's functions at call time only)
from dashboard.steps.step1_run import *  # noqa: F401,F403
from dashboard.steps.step1_run import _budget_summary  # noqa: F401
from dashboard.steps.step1_prep import *  # noqa: F401,F403
from dashboard.steps.step1_director import *  # noqa: F401,F403
from dashboard.steps.step1_director import _director_summary, _replan_button, _paid_line, _crew_notes, _director_review  # noqa: F401
