"""
HTML文本提取器
从HTML内容中提取关键文本，去除HTML标签、脚本、样式等无关内容
"""
from __future__ import annotations

import re
from html import unescape
from typing import Optional


class TextExtractor:
    """从HTML中提取纯文本内容的工具类"""
    
    def __init__(self, max_length: int = 8000):
        self.max_length = max_length
    
    def extract(self, html: str) -> str:
        """
        从HTML中提取关键文本内容
        
        Args:
            html: HTML内容字符串
            
        Returns:
            提取后的纯文本
        """
        if not html:
            return ""
        
        # 1. 移除脚本和样式标签及其内容
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
        
        # 2. 移除所有标签，但保留标签间的文本
        html = re.sub(r'<[^>]+>', ' ', html)
        
        # 3. 处理常见的HTML实体
        html = unescape(html)
        
        # 4. 清理空白字符
        # 合并多个空格
        html = re.sub(r'\s+', ' ', html)
        # 移除首尾空格
        html = html.strip()
        
        # 5. 移除常见的导航、广告等无关文本模式
        patterns_to_remove = [
            r'导航\s*：?\s*[\w\s]*',
            r'首页|主页|关于|联系我们|隐私政策|服务条款|用户协议',
            r'Copyright|版权所有|©\s*\d{4}',
            r'All rights reserved',
            r'返回顶部|回到顶部|Back to top',
            r'广告|推广|赞助|优惠|折扣',
            r'分享到：?\s*(微信|微博|QQ|Facebook|Twitter)',
            r'阅读原文|查看更多|了解更多',
            r'立即报名|点击这里|点击下载',
            r'登录|注册|Sign in|Sign up',
            r'搜索：?\s*[\w\s]*',
            r'热门推荐|相关阅读|猜你喜欢',
        ]
        
        for pattern in patterns_to_remove:
            html = re.sub(pattern, '', html, flags=re.IGNORECASE)
        
        # 6. 再次清理多余的空白
        html = re.sub(r'\s+', ' ', html)
        html = html.strip()
        
        # 7. 截断到最大长度
        if len(html) > self.max_length:
            # 尝试在句子边界处截断
            truncate_point = self._find_sentence_boundary(html, self.max_length)
            html = html[:truncate_point].strip()
        
        return html
    
    def _find_sentence_boundary(self, text: str, max_len: int) -> int:
        """
        在指定长度内找到句子边界
        
        Args:
            text: 文本内容
            max_len: 最大长度
            
        Returns:
            截断位置
        """
        # 首先尝试在句号、问号、感叹号后截断
        for punct in ['。', '.', '！', '!', '？', '?']:
            # 找到在max_len之前的最后一个标点位置
            last_punct = text.rfind(punct, 0, max_len)
            if last_punct != -1 and last_punct > max_len - 100:  # 不要截断太短
                return last_punct + 1
        
        # 如果找不到句子边界，尝试在空格处截断
        last_space = text.rfind(' ', 0, max_len)
        if last_space != -1:
            return last_space
        
        # 如果连空格都找不到，直接截断
        return max_len
    
    def extract_with_importance(
        self, 
        html: str, 
        important_tags: list[str] = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'blockquote', 'article']
    ) -> str:
        """
        提取文本时优先保留重要标签的内容
        
        Args:
            html: HTML内容
            important_tags: 重要的HTML标签列表
            
        Returns:
            提取后的文本
        """
        if not html:
            return ""
        
        # 先提取重要标签的内容
        important_content = []
        
        for tag in important_tags:
            # 匹配标签及其内容
            pattern = f'<{tag}[^>]*>(.*?)</{tag}>'
            matches = re.findall(pattern, html, flags=re.DOTALL | re.IGNORECASE)
            for match in matches:
                # 清理内容
                cleaned = re.sub(r'<[^>]+>', ' ', match)
                cleaned = re.sub(r'\s+', ' ', cleaned).strip()
                if cleaned:
                    important_content.append(cleaned)
        
        # 如果提取到了重要内容，返回它们
        if important_content:
            result = ' '.join(important_content)
            # 应用相同的清理规则
            result = self._clean_text(result)
            if len(result) <= self.max_length:
                return result
            else:
                # 如果重要内容太多，进行截断
                truncate_point = self._find_sentence_boundary(result, self.max_length)
                return result[:truncate_point].strip()
        
        # 如果没有找到重要标签，回退到全文提取
        return self.extract(html)
    
    def _clean_text(self, text: str) -> str:
        """清理文本中的多余空白和无关内容"""
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        # 移除常见的无关短语
        patterns_to_remove = [
            r'广告|推广|赞助|优惠|折扣',
            r'分享到：?\s*(微信|微博|QQ|Facebook|Twitter)',
            r'阅读原文|查看更多|了解更多',
            r'立即报名|点击这里|点击下载',
            r'登录|注册|Sign in|Sign up',
            r'Copyright|版权所有|©\s*\d{4}',
            r'All rights reserved',
            r'返回顶部|回到顶部|Back to top',
        ]
        for pattern in patterns_to_remove:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        # 再次清理空白
        text = re.sub(r'\s+', ' ', text).strip()
        return text


def extract_text_from_html(html: str, max_chars: int = 8000, use_importance: bool = True) -> str:
    """
    便捷函数：从HTML中提取文本
    
    Args:
        html: HTML内容
        max_chars: 最大字符数
        use_importance: 是否使用重要性提取
        
    Returns:
        提取后的文本
    """
    extractor = TextExtractor(max_length=max_chars)
    if use_importance:
        return extractor.extract_with_importance(html)
    else:
        return extractor.extract(html)