from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(slots=True)
class ExtractedArticleContent:
    title: str = ""
    author: str = ""
    image_url: str = ""
    profile_image_url: str = ""
    paragraphs: list[str] = field(default_factory=list)
    blocks: list[tuple[str, str]] = field(default_factory=list)


class ArticleExtractor(Protocol):
    name: str

    def extract(self, url: str) -> ExtractedArticleContent:
        ...


class UnknownArticleExtractorError(ValueError):
    pass


_EXTRACTORS: dict[str, ArticleExtractor] = {}


def register_article_extractor(extractor: ArticleExtractor) -> None:
    _EXTRACTORS[extractor.name] = extractor


def get_article_extractor(name: str) -> ArticleExtractor:
    extractor = _EXTRACTORS.get(name)
    if extractor is None:
        raise UnknownArticleExtractorError(
            f"unknown article extractor: {name}. Registered extractors: {', '.join(sorted(_EXTRACTORS)) or 'none'}"
        )
    return extractor
