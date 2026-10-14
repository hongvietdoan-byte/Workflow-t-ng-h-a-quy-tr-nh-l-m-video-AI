"""Component Đ12v2 độc lập; chưa nối Bước 5 đang do phiên khác giữ."""
from core import features, sfx_plan


def render(p, data_dir, pid, transition='cut', fade=1.0):
    import streamlit as st
    if not features.on('motion_sfx'):
        return
    with st.expander('SFX theo nhịp · code 0 USD'):
        st.caption('Mốc BYĐ ước tính; optical flow không nhận diện động tác. Chưa nối vào Bước 5 sản xuất.')
        if not st.checkbox('Tôi muốn xem gợi ý SFX theo nhịp', key=f'motion_sfx_optin_{pid}'):
            return
        if st.button('Lập gợi ý bằng code · 0 USD', key=f'motion_sfx_propose_{pid}'):
            st.session_state[f'motion_sfx_result_{pid}'] = sfx_plan.propose_motion(
                p, data_dir, pid, transition, fade, opted_in=True)
        result = st.session_state.get(f'motion_sfx_result_{pid}')
        if not result:
            return
        st.write(result['summary'])
        for warning in result['warnings']:
            st.warning(warning)
        st.dataframe(result['cues'])
        if result['unmet']:
            st.warning('Âm/động tác chưa phủ: cần bổ sung Kho hoặc yêu cầu Claude trên luồng có báo giá trước. Component này không gọi Claude.')
            st.dataframe(result['unmet'])
        st.caption('Cue tương thích sfx_plan.apply; chờ nối caller với chọn/duyệt âm hiện có.')
