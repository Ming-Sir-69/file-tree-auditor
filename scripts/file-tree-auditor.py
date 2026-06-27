#!/usr/bin/env python3
"""
File Tree Auditor (file-tree-auditor)

全局文件树审计 & 变动追踪工具。
对任意项目目录运行后，生成：

  - 文件结构概览 (文件树 Markdown)
  - 差异对比报告 (增量 diff)
  - 今日新增清单
  - 月度归档 (按月分组)
  - 每日归档 (按天分组)
  - 加班输出资料 (非工作时间产出分析)
  - JSON 核心数据 (流水线/程序读取用)

用法:
  python3 file-tree-auditor.py --target /path/to/project
  python3 file-tree-auditor.py --target /path/to/project --no-diff

输出文件全部存放在 --target 目录下，文件名前缀自动适配目录名。

零外部依赖 —— 仅需 Python 3 标准库。
"""

import os
import sys
import argparse
import datetime
import json
import re
from collections import defaultdict
from pathlib import Path


# ==========================================
# 配置与常量
# ==========================================

EXCLUDE_KEYWORDS = [
    '_文件结构.md', '_月度归档.md', '_差异对比.md',
    '_今日新增.md', '_每日归档.md', '_加班输出资料.md',
    '_data_structure.json'
]

EXCLUDE_DIRS = {
    '.git', '__pycache__', 'node_modules', '.venv', 'venv',
    '.claude', '.idea', '.vscode', '.trae',
}

DATA_FILE_NAME = '_data_structure.json'

# 加班分析时间窗口
OT_DATE_START = datetime.date(2025, 7, 1)
OT_DATE_END = datetime.date(2026, 6, 26)
OT_AFTER_HOUR = 17
OT_AFTER_MINUTE = 30

# 法定节假日表（硬编码，零依赖）
HOLIDAYS = {
    '2025-10-01': '国庆节', '2025-10-02': '国庆节', '2025-10-03': '国庆节',
    '2025-10-04': '国庆节', '2025-10-05': '中秋节', '2025-10-06': '国庆节',
    '2025-10-07': '国庆节', '2025-10-08': '国庆节',
    '2026-01-01': '元旦', '2026-01-02': '元旦', '2026-01-03': '元旦',
    '2026-02-15': '春节(除夕)', '2026-02-16': '春节(初一)', '2026-02-17': '春节',
    '2026-02-18': '春节', '2026-02-19': '春节', '2026-02-20': '春节',
    '2026-02-21': '春节', '2026-02-22': '春节', '2026-02-23': '春节',
    '2026-04-04': '清明节', '2026-04-05': '清明节', '2026-04-06': '清明节',
    '2026-05-01': '劳动节', '2026-05-02': '劳动节', '2026-05-03': '劳动节',
    '2026-05-04': '劳动节', '2026-05-05': '劳动节',
    '2026-06-19': '端午节', '2026-06-20': '端午节', '2026-06-21': '端午节',
}

# 调休补班日（周末上班）
MAKEUP_WORKDAYS = {
    '2025-09-28': '国庆调休(周日上班)', '2025-10-11': '国庆调休(周六上班)',
    '2026-02-14': '春节调休(周六上班)', '2026-02-28': '春节调休(周六上班)',
    '2026-05-09': '劳动节调休(周六上班)',
}


# ==========================================
# JSON 数据源管理
# ==========================================

def load_json_record(json_path: Path):
    if not json_path.exists():
        return None
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if 'files' in data:
            return data['files']
        return data
    except Exception as e:
        print(f"[警告] 读取数据文件失败: {e}")
        return None


def save_json_record(data_map, json_path: Path):
    structure = {
        "version": "3.0",
        "tool": "file-tree-auditor",
        "timestamp": datetime.datetime.now().timestamp(),
        "target": str(json_path.parent.resolve()),
        "files": data_map,
    }
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(structure, f, indent=2, ensure_ascii=False)
        print(f"[数据] 已更新核心数据文件: {json_path.name}")
    except Exception as e:
        print(f"[错误] 保存数据文件失败: {e}")


# ==========================================
# 文件扫描（双时间戳）
# ==========================================

def collect_all_files(root_path: Path):
    all_files = {}
    count = 0
    print(f"[扫描] 开始扫描目录: {root_path}")
    for parent, dirs, files in os.walk(root_path):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        parent_path = Path(parent)
        for name in files:
            if any(k in name for k in EXCLUDE_KEYWORDS):
                continue
            full_path = parent_path / name
            try:
                stat = full_path.stat()
                rel_path = str(full_path.relative_to(root_path))
                all_files[rel_path] = {
                    'mtime': stat.st_mtime,
                    'birthtime': getattr(stat, 'st_birthtime', stat.st_mtime),
                    'size': stat.st_size,
                }
                count += 1
            except Exception:
                continue
    print(f"[扫描] 完成: {count} 个文件")
    return all_files


# ==========================================
# 差异分析
# ==========================================

def calculate_diff(old_map, new_map):
    diff = {'added': [], 'removed': [], 'modified': [], 'moved': []}
    old_keys = set(old_map.keys())
    new_keys = set(new_map.keys())

    for k in old_keys & new_keys:
        o, n = old_map[k], new_map[k]
        time_diff = abs(n['mtime'] - o['mtime'])
        is_modified = False
        if time_diff > 60:
            is_modified = True
        if o.get('size') is not None and n.get('size') is not None and o['size'] != n['size']:
            is_modified = True
        if is_modified:
            diff['modified'].append((k, n['mtime']))

    potential_added = list(new_keys - old_keys)
    potential_removed = list(old_keys - new_keys)

    added_by_name = {}
    for p in potential_added:
        name = Path(p).name
        added_by_name.setdefault(name, []).append(p)

    final_added = []
    final_removed = set(potential_removed)
    matched_added = set()
    moves = []

    for rem_path in potential_removed:
        name = Path(rem_path).name
        candidates = [c for c in added_by_name.get(name, []) if c not in matched_added]
        if not candidates:
            continue
        rem_info = old_map[rem_path]
        best_match = None
        match_type = None

        for cand in candidates:
            ci = new_map[cand]
            if abs(ci['mtime'] - rem_info['mtime']) <= 60:
                size_ok = (rem_info.get('size') is None or ci.get('size') is None
                           or rem_info['size'] == ci['size'])
                if size_ok:
                    best_match = cand
                    match_type = 'pure'
                    break

        if not best_match and len(candidates) == 1:
            best_match = candidates[0]
            match_type = 'modified'

        if best_match:
            moves.append({'from': rem_path, 'to': best_match, 'type': match_type,
                          'mtime': new_map[best_match]['mtime']})
            matched_added.add(best_match)
            final_removed.discard(rem_path)

    for p in potential_added:
        if p not in matched_added:
            final_added.append((p, new_map[p]['mtime']))

    diff['added'] = final_added
    diff['removed'] = [(p, old_map[p]['mtime']) for p in final_removed]
    diff['moved'] = moves
    return diff


# ==========================================
# 格式化与树渲染
# ==========================================

def format_time(mtime):
    if mtime is None:
        return ""
    try:
        return datetime.datetime.fromtimestamp(mtime).strftime('%Y/%m/%d %H:%M')
    except Exception:
        return ""


def build_virtual_tree(file_list):
    tree = {}
    for rel_path, mtime in file_list:
        parts = Path(rel_path).parts
        cur = tree
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                cur[part] = {'__type__': 'file', 'mtime': mtime}
            else:
                if part not in cur:
                    cur[part] = {'__type__': 'dir', 'children': {}}
                if cur[part].get('__type__') == 'file':
                    cur[part] = {'__type__': 'dir', 'children': {}}
                cur = cur[part]['children']
    return tree


def draw_virtual_tree(out, node, prefix_state):
    items = sorted(node.items(), key=lambda x: x[0].casefold())
    dirs_ = [(n, i) for n, i in items if i.get('__type__') == 'dir']
    files_ = [(n, i) for n, i in items if i.get('__type__') != 'dir']
    children = dirs_ + files_
    for idx, (name, info) in enumerate(children):
        is_last = (idx == len(children) - 1)
        indent = ''.join('│   ' if v else '    ' for v in prefix_state)
        branch = '└──' if is_last else '├──'
        mtime = info.get('mtime')
        label = name + (f"  {format_time(mtime)}" if mtime else "")
        out.write(f"{indent}{branch} {label}\n")
        if info.get('__type__') == 'dir':
            draw_virtual_tree(out, info.get('children', {}), prefix_state + [not is_last])


def draw_real_tree(out, dir_path: Path, prefix_state):
    try:
        entries = list(os.scandir(dir_path))
    except Exception:
        return
    dirs_ = []
    files_ = []
    for e in entries:
        if any(k in e.name for k in EXCLUDE_KEYWORDS) or e.name in EXCLUDE_DIRS:
            continue
        try:
            if e.is_dir(follow_symlinks=False):
                dirs_.append(e)
            else:
                files_.append(e)
        except Exception:
            pass
    dirs_.sort(key=lambda x: x.name.casefold())
    files_.sort(key=lambda x: x.name.casefold())
    children = dirs_ + files_
    for idx, e in enumerate(children):
        is_last = (idx == len(children) - 1)
        indent = ''.join('│   ' if v else '    ' for v in prefix_state)
        branch = '└──' if is_last else '├──'
        label = e.name
        try:
            label += f"  {format_time(e.stat().st_mtime)}"
        except Exception:
            pass
        out.write(f"{indent}{branch} {label}\n")
        if e.is_dir(follow_symlinks=False):
            draw_real_tree(out, Path(e.path), prefix_state + [not is_last])


# ==========================================
# 加班分析（零外部依赖，硬编码节假日）
# ==========================================

def is_non_human_file(rel_path):
    name = Path(rel_path).name
    ext = Path(rel_path).suffix.lower()
    if name in {'.DS_Store', 'Thumbs.db', '.localized', 'desktop.ini'}:
        return True
    if ext in {'.pyc', '.pyo', '.swp', '.swo', '.tmp', '.temp'}:
        return True
    for d in Path(rel_path).parts:
        if d in EXCLUDE_DIRS:
            return True
    return False


def classify_overtime(dt):
    """零依赖版本：用硬编码节假日判断"""
    date_obj = dt.date()
    time_obj = dt.time()
    if date_obj < OT_DATE_START or date_obj > OT_DATE_END:
        return (False, None, '')
    date_str = date_obj.strftime('%Y-%m-%d')
    if date_str in MAKEUP_WORKDAYS:
        # 调休补班日：按工作日处理
        if time_obj.hour > OT_AFTER_HOUR or (time_obj.hour == OT_AFTER_HOUR and time_obj.minute >= OT_AFTER_MINUTE):
            return (True, 'after_hours', '调休补班日加班')
        return (False, None, '')
    if date_str in HOLIDAYS:
        return (True, 'holiday', HOLIDAYS[date_str])
    if dt.weekday() >= 5:
        return (True, 'weekend', '周末')
    if time_obj.hour > OT_AFTER_HOUR or (time_obj.hour == OT_AFTER_HOUR and time_obj.minute >= OT_AFTER_MINUTE):
        return (True, 'after_hours', '工作日下班后')
    return (False, None, '')


def generate_ot_report(data_map, root, output_path):
    """生成加班输出资料（纯文本版，无图表）"""
    print("\n[6/6] 生成加班输出资料...")

    records = []
    for rel_path, info in data_map.items():
        mtime = info.get('mtime')
        if mtime is None or is_non_human_file(rel_path):
            continue
        dt_m = datetime.datetime.fromtimestamp(mtime)
        is_ot, cat, detail = classify_overtime(dt_m)
        if is_ot:
            records.append((rel_path, mtime, cat, detail, 'mtime'))
        birthtime = info.get('birthtime')
        if birthtime is not None and abs(birthtime - mtime) > 60:
            dt_b = datetime.datetime.fromtimestamp(birthtime)
            is_ot, cat, detail = classify_overtime(dt_b)
            if is_ot:
                records.append((rel_path, birthtime, cat, detail, 'birthtime'))

    holiday_recs = [(p, m, d) for p, m, cat, d, _ in records if cat == 'holiday']
    weekend_recs = [(p, m) for p, m, cat, d, _ in records if cat == 'weekend']
    after_hours_recs = [(p, m, d) for p, m, cat, d, _ in records if cat == 'after_hours']
    total = len(records)

    print(f"   ├─ 法定节假日加班: {len(holiday_recs)}")
    print(f"   ├─ 周末加班:       {len(weekend_recs)}")
    print(f"   └─ 工作日下班后加班: {len(after_hours_recs)}")
    print(f"   → 加班总计: {total} 文件")

    # 按日期统计
    ot_by_date = defaultdict(list)
    for p, m, cat, d, _ in records:
        ot_by_date[datetime.datetime.fromtimestamp(m).strftime('%Y-%m-%d')].append((p, m, cat, d))

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# 加班输出资料\n\n")
            f.write(f"> 分析范围: {OT_DATE_START} ~ {OT_DATE_END}\n")
            f.write(f"> 生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"> 下班时间线: 工作日（含调休补班）{OT_AFTER_HOUR:02d}:{OT_AFTER_MINUTE:02d} 后\n")
            f.write(f"> 已排除: 系统文件(.DS_Store等)·编译缓存(.pyc等)·IDE配置目录(.trae/.vscode/.claude)\n")
            f.write("> 注: 基于硬编码节假日判断（无 chinese_calendar 依赖），如有调休变化请手动更新 HOLIDAYS 表\n\n")

            f.write("## 一、统计概览\n\n")
            f.write("| 类别 | 文件数 | 说明 |\n")
            f.write("|------|--------|------|\n")
            f.write(f"| 法定节假日 | {len(holiday_recs)} | 国定假日内发生的文件操作 |\n")
            f.write(f"| 周末 | {len(weekend_recs)} | 周六/周日（不含调休补班日） |\n")
            f.write(f"| 工作日下班后 | {len(after_hours_recs)} | 工作日（含补班日）{OT_AFTER_HOUR:02d}:{OT_AFTER_MINUTE:02d} 后 |\n")
            f.write(f"| **合计** | **{total}** | （已排除系统/IDE自动生成的元文件） |\n\n")

            f.write(f"加班总天数: {len(ot_by_date)} 天\n\n")
            for dk in sorted(ot_by_date.keys(), reverse=True):
                entries = ot_by_date[dk]
                dtw = datetime.datetime.strptime(dk, '%Y-%m-%d')
                wd = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][dtw.weekday()]
                cats = {}
                for _, _, cat, detail in entries:
                    cats[cat] = cats.get(cat, 0) + 1
                cat_desc = ' | '.join(f"{k}:{v}" for k, v in cats.items())
                f.write(f"- **{dk} ({wd})** → {len(entries)} 文件 [{cat_desc}]\n")
            f.write("\n")

            if holiday_recs:
                f.write("---\n## 二、法定节假日加班输出资料\n\n")
                by_holiday = {}
                for p, m, h in holiday_recs:
                    by_holiday.setdefault(h, []).append((p, m))
                for h_name in sorted(by_holiday.keys()):
                    h_files = by_holiday[h_name]
                    f.write(f"### {h_name} ({len(h_files)} 文件)\n\n")
                    f.write("```text\n")
                    draw_virtual_tree(f, build_virtual_tree(h_files), [])
                    f.write("```\n\n")

            if weekend_recs:
                f.write("---\n## 三、周末加班输出资料\n\n")
                by_wk = {}
                for p, m in weekend_recs:
                    by_wk[datetime.datetime.fromtimestamp(m).strftime('%Y-%m-%d')].append((p, m))
                for dk in sorted(by_wk.keys(), reverse=True):
                    wk_files = by_wk[dk]
                    dtw = datetime.datetime.strptime(dk, '%Y-%m-%d')
                    wd = ['周六', '周日'][dtw.weekday() - 5]
                    f.write(f"### {dk} ({wd}) - {len(wk_files)} 文件\n\n")
                    f.write("```text\n")
                    draw_virtual_tree(f, build_virtual_tree(wk_files), [])
                    f.write("```\n\n")

            if after_hours_recs:
                f.write("---\n## 四、工作日下班后加班输出资料\n\n")
                by_ah = {}
                for p, m, r in after_hours_recs:
                    by_ah[datetime.datetime.fromtimestamp(m).strftime('%Y-%m-%d')].append((p, m, r))
                for dk in sorted(by_ah.keys(), reverse=True):
                    ah_files = [(p, m) for p, m, _ in by_ah[dk]]
                    f.write(f"### {dk} ({len(ah_files)} 文件)\n\n")
                    f.write("```text\n")
                    draw_virtual_tree(f, build_virtual_tree(ah_files), [])
                    f.write("```\n\n")

        print(f"-> 加班输出资料已生成: {output_path.name}")
    except Exception as e:
        print(f"-> 加班输出资料生成失败: {e}")


# ==========================================
# 报告生成
# ==========================================

def write_diff_report(path, diff):
    added = diff['added']
    removed = diff['removed']
    modified = diff['modified']
    moved = diff['moved']
    has_changes = any([added, removed, modified, moved])

    with open(path, 'w', encoding='utf-8') as f:
        f.write("# 文件差异对比报告\n\n")
        f.write(f"生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        if not has_changes:
            f.write("自上次记录以来，文件结构无变化。\n")
            return

        f.write(f"## 移动/重命名 ({len(moved)})\n")
        if moved:
            for m in moved:
                icon = "(已修改)" if m['type'] == 'modified' else "→"
                f.write(f"- `{m['from']}` {icon} `{m['to']}`\n")
        f.write(f"\n## 新增 ({len(added)})\n")
        if added:
            f.write("```text\n")
            draw_virtual_tree(f, build_virtual_tree(added), [])
            f.write("```\n")
        f.write(f"\n## 修改 ({len(modified)})\n")
        if modified:
            f.write("```text\n")
            draw_virtual_tree(f, build_virtual_tree(modified), [])
            f.write("```\n")
        f.write(f"\n## 删除 ({len(removed)})\n")
        if removed:
            f.write("```text\n")
            draw_virtual_tree(f, build_virtual_tree(removed), [])
            f.write("```\n")

    print(f"[差异] 报告已生成: {path.name}")


def write_daily_report(path, current_map):
    now = datetime.datetime.now()
    today_start = datetime.datetime(now.year, now.month, now.day).timestamp()
    today_files = [(p, info['mtime']) for p, info in current_map.items()
                   if today_start <= info['mtime'] < today_start + 86400]
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f"# {now.strftime('%Y-%m-%d')} 今日变动文件\n\n")
        if not today_files:
            f.write("今日无文件变动。\n")
        else:
            f.write("```text\n")
            draw_virtual_tree(f, build_virtual_tree(today_files), [])
            f.write("```\n")


def write_tree_view(path, root_name, real_root):
    with open(path, 'w', encoding='utf-8') as f:
        f.write("```text\n")
        f.write(f"{root_name}\n")
        draw_real_tree(f, real_root, [])
        f.write("```\n")
    print(f"[结构] 视图已生成: {path.name}")


def write_monthly_archive(path, current_map):
    grouped = {}
    for p, info in current_map.items():
        try:
            key = datetime.datetime.fromtimestamp(info['mtime']).strftime('%Y-%m')
        except Exception:
            key = "Unknown"
        grouped.setdefault(key, []).append((p, info['mtime']))
    with open(path, 'w', encoding='utf-8') as f:
        for month in sorted(grouped.keys(), reverse=True):
            files_in_month = grouped[month]
            f.write(f"# {month} ({len(files_in_month)} files)\n\n")
            f.write("```text\n")
            draw_virtual_tree(f, build_virtual_tree(files_in_month), [])
            f.write("```\n\n")


def write_daily_archive(path, current_map):
    grouped = {}
    for p, info in current_map.items():
        try:
            key = datetime.datetime.fromtimestamp(info['mtime']).strftime('%Y-%m-%d')
        except Exception:
            key = "Unknown"
        grouped.setdefault(key, []).append((p, info['mtime']))
    with open(path, 'w', encoding='utf-8') as f:
        for day in sorted(grouped.keys(), reverse=True):
            files_in_day = grouped[day]
            f.write(f"# {day} ({len(files_in_day)} files)\n\n")
            f.write("```text\n")
            draw_virtual_tree(f, build_virtual_tree(files_in_day), [])
            f.write("```\n\n")


# ==========================================
# 主入口
# ==========================================

def run(target_path: str, no_diff: bool = False):
    root = Path(target_path).resolve()
    if not root.is_dir():
        print(f"[错误] 路径不存在或不是目录: {root}")
        sys.exit(1)

    dir_name = root.name
    print("=" * 48)
    print(f"  File Tree Auditor")
    print(f"  目标: {root}")
    print("=" * 48)

    # 输出文件路径
    data_json = root / DATA_FILE_NAME
    paths = {
        'struct': root / f"{dir_name}_文件结构.md",
        'diff': root / f"{dir_name}_差异对比.md",
        'daily': root / f"{dir_name}_今日新增.md",
        'month': root / f"{dir_name}_月度归档.md",
        'day_arch': root / f"{dir_name}_每日归档.md",
        'ot': root / f"{dir_name}_加班输出资料.md",
    }

    print("\n[1/5] 扫描文件系统...")
    current_map = collect_all_files(root)

    print("\n[2/5] 加载历史数据...")
    old_map = load_json_record(data_json)
    if old_map is None:
        print("  -> 无历史记录，首次运行（将跳过差异对比）")

    if no_diff:
        print("\n[3/5] 跳过差异报告 (--no-diff)")
    else:
        print("\n[3/5] 生成差异分析...")
        if not old_map:
            with open(paths['diff'], 'w', encoding='utf-8') as f:
                f.write("# 文件差异对比报告\n\n初始化运行，建立基准数据。下次运行将显示差异。\n")
        else:
            diff = calculate_diff(old_map, current_map)
            write_diff_report(paths['diff'], diff)

    print("\n[4/5] 生成今日变动报告...")
    write_daily_report(paths['daily'], current_map)

    print("\n[5/5] 更新数据与归档...")
    save_json_record(current_map, data_json)
    write_tree_view(paths['struct'], dir_name, root)
    write_monthly_archive(paths['month'], current_map)
    write_daily_archive(paths['day_arch'], current_map)

    # 加班输出资料
    generate_ot_report(current_map, root, paths['ot'])

    print("\n" + "=" * 48)
    print(f"  完成！所有报告输出至: {root}")
    print(f"  生成文件: {dir_name}_文件结构.md")
    print(f"            {dir_name}_差异对比.md")
    print(f"            {dir_name}_今日新增.md")
    print(f"            {dir_name}_月度归档.md")
    print(f"            {dir_name}_每日归档.md")
    print(f"            {dir_name}_加班输出资料.md")
    print("=" * 48)


def main():
    parser = argparse.ArgumentParser(
        description="File Tree Auditor — 文件结构审计与变动追踪",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--target', '-t', required=True, help='目标项目目录路径')
    parser.add_argument('--no-diff', action='store_true', help='跳过差异对比（首次运行或重置基线）')
    args = parser.parse_args()
    run(args.target, no_diff=args.no_diff)


if __name__ == '__main__':
    main()
