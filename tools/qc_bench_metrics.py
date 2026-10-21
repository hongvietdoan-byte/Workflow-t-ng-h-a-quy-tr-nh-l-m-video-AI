"""Số đo QC thuần offline; không xác minh người gán nhãn, không xét BLOCK.

Schema tối thiểu: case_id, qc_code, artifact_sha, label, split, prediction.
Prediction error/pass/doubt; doubt là abstain, nhãn LOI doubt vẫn là FN.
ECE đo độ tin cậy của quyết định error/pass đúng; doubt không có quyết định
nên loại khỏi ECE và đếm riêng. KHONG_XET loại khỏi mọi mẫu số số đo.
"""
import math
import re


def _ratio(a, b):
    return a / b if b else None


def _wilson(k, n):
    if not n:
        return None
    z = 1.959963984540054
    p = k / n
    d = 1 + z*z/n
    center = (p + z*z/(2*n)) / d
    radius = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return (max(0., center-radius), min(1., center+radius))


def score_cases(cases):
    """Trả số đo theo mã; đầu vào chỉ là bản ghi do caller cung cấp.

    Không tự coi label_by là bằng chứng xác minh; caller phải lọc nhãn người
    đã xác nhận trước khi dùng kết quả chính thức. Chặn SHA lọt hai split
    trên toàn bộ đầu vào, kể cả KHONG_XET và khác mã QC.
    """
    groups, splits = {}, {}
    for case in cases:
        for key in ('case_id', 'qc_code'):
            if not isinstance(case.get(key), str) or not case[key].strip():
                raise ValueError(f'Thiếu {key}')
        sha = case.get('artifact_sha')
        if not isinstance(sha, str) or not re.fullmatch(r'[0-9a-fA-F]{64}', sha):
            raise ValueError('artifact_sha phải là SHA256')
        sha = sha.lower()
        if case.get('label') not in ('LOI', 'DAT', 'KHONG_XET'):
            raise ValueError('Nhãn không hợp lệ')
        if case.get('split') not in ('dev', 'independent'):
            raise ValueError('Split không hợp lệ')
        if case.get('prediction') not in ('error', 'pass', 'doubt'):
            raise ValueError('Dự đoán không hợp lệ')
        if sha in splits and splits[sha] != case['split']:
            raise ValueError('artifact_sha trùng giữa hai split')
        splits[sha] = case['split']
        confidence = case.get('confidence')
        if confidence is not None and (type(confidence) not in (int, float)
                or not math.isfinite(confidence) or not 0 <= confidence <= 1):
            raise ValueError('confidence phải hữu hạn trong [0,1]')
        groups.setdefault(case['qc_code'], []).append(case)
    if len(set(splits.values())) > 1:
        raise ValueError('Phải chọn một split trước khi tính metrics')
    result = {}
    for code, rows in groups.items():
        m = dict.fromkeys(('tp', 'fp', 'fn', 'tn', 'abstain', 'n_pos', 'n_neg',
                           'excluded', 'confidence_excluded_doubt'), 0)
        bins = [[] for _ in range(5)]
        for r in rows:
            if r['label'] == 'KHONG_XET':
                m['excluded'] += 1
                continue
            positive = r['label'] == 'LOI'
            pred = r['prediction']
            m['n_pos' if positive else 'n_neg'] += 1
            if pred == 'doubt':
                m['abstain'] += 1
                if positive:
                    m['fn'] += 1
                if r.get('confidence') is not None:
                    m['confidence_excluded_doubt'] += 1
            else:
                key = ('tp' if positive else 'fp') if pred == 'error' else ('fn' if positive else 'tn')
                m[key] += 1
                conf = r.get('confidence')
                if conf is not None:
                    bins[min(4, int(conf * 5))].append((conf, int((pred == 'error') == positive)))
        m.update(precision=_ratio(m['tp'], m['tp']+m['fp']),
                 recall=_ratio(m['tp'], m['n_pos']), fpr=_ratio(m['fp'], m['n_neg']),
                 fnr=_ratio(m['fn'], m['n_pos']),
                 doubt_rate=_ratio(m['abstain'], m['n_pos']+m['n_neg']),
                 precision_wilson95=_wilson(m['tp'], m['tp']+m['fp']),
                 recall_wilson95=_wilson(m['tp'], m['n_pos']))
        m['confidence_bins'] = [dict(n=len(b), confidence=_ratio(sum(c for c, _ in b), len(b)),
                                     accuracy=_ratio(sum(a for _, a in b), len(b))) for b in bins]
        n = sum(len(b) for b in bins)
        m['ece'] = sum(b['n'] * abs(b['accuracy']-b['confidence']) for b in m['confidence_bins'] if b['n']) / n if n else None
        m['label_verification'] = 'NOT_ASSESSED'
        result[code] = m
    return result
