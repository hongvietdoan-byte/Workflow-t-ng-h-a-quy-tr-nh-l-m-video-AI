"""Gợi ý code SFX theo nhịp, dùng bảng chọn/duyệt chung của Bước 5."""
from core import access, features, sfx_plan


def render(p, data_dir, pid, transition='cut', fade=1.0):
    import streamlit as st
    if not features.on('motion_sfx'):
        return
    editable = access.can_edit(p.conn, pid, getattr(p, 'user', None))
    if st.button('Lập gợi ý theo nhịp · code 0 USD', key=f'motion_sfx_propose_{pid}', disabled=not editable):
        try:
            access.need_edit(p, pid, 'lập gợi ý SFX theo nhịp')
            with st.spinner('Đang đo clip và đối chiếu BYĐ với Kho…'):
                result = sfx_plan.propose_motion_review(p, data_dir, pid, transition, fade)
            if result is not None:
                st.session_state.pop(f'sfx_table_{pid}', None)
                st.session_state[f'sfxplan_{pid}'] = result
        except (sfx_plan.SfxPlanError, access.AccessDenied, ValueError) as e:
            st.error(str(e))
    st.caption('Chỉ gợi ý, chưa áp âm. Mốc hoạt động khung không chứng minh động tác; cần chọn và duyệt bên dưới.')


def show_details(st, plan):
    for warning in plan.get('warnings', []):
        st.warning(warning)
    if plan.get('unmet'):
        st.warning('Âm/động tác chưa phủ: bổ sung Kho hoặc dùng nút AI có ước tính phí; không tự gọi Claude.')
        st.dataframe(plan['unmet'], hide_index=True, width='stretch')
    with st.expander('Mốc đo clip / BYĐ ước tính'):
        st.dataframe(plan.get('measurements', []), hide_index=True, width='stretch')
