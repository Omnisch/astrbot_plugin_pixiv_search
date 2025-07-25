"""
tag.py
统一Pixiv标签格式化、详情信息构建与R18/AI过滤工具模块
"""

# R18 与 AI Badwords List
R18_BADWORDS = [s.lower() for s in ["R-18", "R18", "R-18G", "R18G", "R18+", "R18+G"]]
AI_BADWORDS = [s.lower() for s in ["AI", "AI生成", "AI-generated", "AI辅助"]]


def is_r18(item):
    tags = getattr(item, "tags", [])
    for tag in tags:
        name = tag.get("name") if isinstance(tag, dict) else tag
        if isinstance(name, str):
            lname = name.lower()
            if any(bad in lname for bad in R18_BADWORDS):
                return True
    return False


def is_ai(item):
    tags = getattr(item, "tags", [])
    for tag in tags:
        name = tag.get("name") if isinstance(tag, dict) else tag
        if isinstance(name, str):
            lname = name.lower()
            if any(bad in lname for bad in AI_BADWORDS):
                return True
    return False

def filter_illusts_with_reason(
    illusts,
    r18_mode,
    ai_filter_mode,
    display_tag_str=None,
    first_tag=None,
    all_illusts_from_first_tag=None,
    return_count=1,
    logger=None,
    show_filter_result=True,
    excluded_tags=None,
):
    """
    统一R18/AI/排除标签过滤逻辑，返回过滤后的插画列表和详细过滤提示（如需）。
    """
    initial_count = len(illusts)
    filtered_list = []
    excluded_tags = excluded_tags or []
    
    for illust in illusts:
        if r18_mode == "过滤 R18" and is_r18(illust):
            continue
        if r18_mode == "仅 R18" and not is_r18(illust):
            continue
        if ai_filter_mode == "过滤 AI 作品" and is_ai(illust):
            continue
        if ai_filter_mode == "仅 AI 作品" and not is_ai(illust):
            continue
        if excluded_tags and has_excluded_tags(illust, excluded_tags):
            continue
        filtered_list.append(illust)
    
    filtered_count = len(filtered_list)
    filter_msgs = []
    if not show_filter_result:
        return filtered_list, []
    
    # 过滤信息提示
    if filtered_count < initial_count:
        filter_reasons = []
        if r18_mode == "过滤 R18" or r18_mode == "仅 R18":
            filter_reasons.append("R18")
        if ai_filter_mode == "过滤 AI 作品" or ai_filter_mode == "仅 AI 作品":
            filter_reasons.append("AI")
        if excluded_tags:
            filter_reasons.append("排除标签")
        if filter_reasons:
            filter_msgs.append(
                f"部分作品因 {'/'.join(filter_reasons)} 设置被过滤 (找到 {initial_count} 个符合所有标签的作品，最终剩 {filtered_count} 个可发送)。"
            )
    elif initial_count > 0:
        filter_msgs.append(
            f"筛选完成，共找到 {initial_count} 个符合所有标签「{display_tag_str or ''}」的作品。正在发送最多 {return_count} 张..."
        )
    
    # 结果为空时详细原因
    if not filtered_list:
        no_result_reason = []
        if r18_mode == "过滤 R18" and any(is_r18(i) for i in illusts):
            no_result_reason.append("R18 内容")
        if ai_filter_mode == "过滤 AI 作品" and any(is_ai(i) for i in illusts):
            no_result_reason.append("AI 作品")
        if r18_mode == "仅 R18" and not any(is_r18(i) for i in illusts):
            no_result_reason.append("非 R18 内容")
        if ai_filter_mode == "仅 AI 作品" and not any(is_ai(i) for i in illusts):
            no_result_reason.append("非 AI 作品")
        if excluded_tags and any(has_excluded_tags(i, excluded_tags) for i in illusts):
            no_result_reason.append("包含排除标签")
        if no_result_reason and initial_count > 0:
            filter_msgs.append(
                f"所有找到的作品均为 {' 或 '.join(no_result_reason)}，根据当前设置已被过滤。"
            )
        elif (
            initial_count == 0
            and all_illusts_from_first_tag is not None
            and len(all_illusts_from_first_tag) > 0
        ):
            filter_msgs.append(
                f"找到了与「{first_tag}」相关的作品，但没有作品同时包含所有标签「{display_tag_str}」。"
            )
        elif (
            initial_count == 0
            and all_illusts_from_first_tag is not None
            and len(all_illusts_from_first_tag) == 0
        ):
            filter_msgs.append(f"未找到任何与标签「{first_tag}」相关的作品。")
        else:
            if logger:
                logger.warning(
                    "AND 深度搜索后没有符合条件的插画可供发送，但过滤原因不明确。"
                )
            filter_msgs.append("筛选后没有符合条件的作品可发送。")
    return filtered_list, filter_msgs

def format_tags(tags) -> str:
    """
    将Pixiv标签结构（支持list/dict/str）格式化为:
    R-18, 尘白禁区(Snowbreak), snowbreak, スノウブレイク(Snowbreak), ...
    """
    result = []
    if isinstance(tags, list):
        for tag in tags:
            if isinstance(tag, dict):
                name = tag.get("name", "")
                trans = tag.get("translated_name", "")
                if trans:
                    result.append(f"{name}({trans})")
                else:
                    result.append(name)
            elif isinstance(tag, str):
                result.append(tag)
    elif isinstance(tags, dict):
        name = tags.get("name", "")
        trans = tags.get("translated_name", "")
        if trans:
            result.append(f"{name}({trans})")
        else:
            result.append(name)
    elif isinstance(tags, str):
        result.append(tags)
    return ", ".join([t for t in result if t]) if result else "无"


def build_detail_message(item, is_novel=False):
    """
    构建Pixiv作品详情信息：
    - 插画：标题/作者/标签/链接
    - 小说：小说标题/作者/标签/字数/系列/链接（缺失字段自动省略）
    """
    if is_novel:
        title = getattr(item, "title", "")
        author = getattr(item, "user", None)
        if author and hasattr(author, "name"):
            author = author.name
        else:
            author = getattr(item, "author", "未知")
        tags_str = format_tags(getattr(item, "tags", []))
        text_length = getattr(item, "text_length", None)
        if text_length is None:
            text_length = getattr(item, "word_count", "未知")
        series = getattr(item, "series", None)
        if series and hasattr(series, "title"):
            series_title = series.title
        elif isinstance(series, dict):
            series_title = series.get("title", "未知")
        elif isinstance(series, str) and series:
            series_title = series
        elif series:
            series_title = str(series)
        else:
            series_title = "未知"
        link = f"https://www.pixiv.net/novel/show.php?id={item.id}"
        detail_message = (
            f"小说标题: {title}\n"
            f"作者: {author}\n"
            f"标签: {tags_str}\n"
            f"字数: {text_length}\n"
            f"系列: {series_title}\n"
            f"链接: {link}"
        )
        return detail_message
    else:
        title = getattr(item, "title", "")
        author = getattr(item, "user", None)
        if author and hasattr(author, "name"):
            author = author.name
        else:
            author = getattr(item, "author", "")
        tags_str = format_tags(getattr(item, "tags", []))
        link = f"https://www.pixiv.net/artworks/{item.id}"
        return f"标题: {title}\n作者: {author}\n标签: {tags_str}\n链接: {link}"

def has_excluded_tags(item, excluded_tags):
    """
    检查作品是否包含需要排除的标签
    
    Args:
        item: Pixiv作品对象
        excluded_tags: 需要排除的标签列表（已转换为小写）
    
    Returns:
        bool: 如果包含排除标签返回True，否则返回False
    """
    if not excluded_tags:
        return False
        
    tags = getattr(item, "tags", [])
    for tag in tags:
        name = tag.get("name") if isinstance(tag, dict) else tag
        if isinstance(name, str):
            lname = name.lower()
            if any(excluded_tag in lname for excluded_tag in excluded_tags):
                return True
    return False
