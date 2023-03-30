"""Tools for generating newspaper articles."""
import re

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional

import openai
from jinja2 import Environment, FileSystemLoader

HERE = Path(__file__).parent


@dataclass
class ArticleBlock:
    """Contains an article's contents."""

    text: Optional[str] = None
    picture: Optional[Path] = None

    def __post_init__(self):
        if (self.text is None) == (self.picture is None):
            raise ValueError("Must set either text or picture.")


@dataclass
class Article:
    """Handle an article's contents."""

    title: str
    content: List[ArticleBlock]
    author: str = None
    full_header: bool = False


@dataclass
class Newspaper:
    """Handle a newspaper's contents."""

    title: str
    date: str
    volume: int
    issue: int
    price: str
    articles: List[Article]
    location: str = ""
    full_header: bool = False
    num_cols: int = 3
    big_headline_size: int = 50

    def __post_init__(self):
        if self.full_header:
            self.articles[0].full_header = True

    def render(self) -> str:
        """Get a formatted newspaper!"""

        # Load the template file and perform the regex substitution
        template_content = Path(
            HERE / "templates/newspaper-template/template.j2"
        ).read_text()
        template_content = re.sub(
            r"(\{+)\{{2}([^\}]+)(\}+)\}{2}",
            r"{{ '\g<1>' }}{{ \g<2> }}{{ '\g<3>' }}",
            template_content,
        )

        # Create a Jinja environment with the folder where the template is stored
        env = Environment(
            loader=FileSystemLoader(HERE / "templates/newspaper-template"),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Load the Jinja template
        template = env.from_string(template_content)

        # Format the template with the data
        return template.render(asdict(self))


if __name__ == "__main__":
    article_texts = ["Some example text.", "Some more example text."]
    article_blocks = [ArticleBlock(text) for text in article_texts]
    article_1 = Article("An example title", article_blocks, "Mabel Sneaker")
    article_2 = Article("An example title", article_blocks)
    paper = Newspaper("The Example Weekly", "Today", 6, 9, "Free!", [article_2, article_1], full_header=True, big_headline_size=90)
    example_output = Path("example_paper.tex")
    example_output.write_text(paper.render())
