"""Tools for generating newspaper articles."""
import re

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional

import openai
from jinja2 import Environment, FileSystemLoader

HERE = Path(__file__).parent

# Create a Jinja environment with the folder where the templates are stored
JINJA_ENV = Environment(
    loader=FileSystemLoader(HERE / "templates/newspaper-template"),
    trim_blocks=True,
    lstrip_blocks=True,
)


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
    author: Optional[str] = None
    full_header: bool = False

    def __post_init__(self):
        if self.author is None:
            self.author = ""


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
        self.articles[0].full_header = self.full_header
        for article in self.articles[1:]:
            article.full_header = False

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

        # Load the Jinja template
        template = JINJA_ENV.from_string(template_content)

        # Format the template with the data
        return template.render(asdict(self))


@dataclass
class PaperConfig:
    source_files: List[Path]
    title: str
    date: str
    volume: int
    issue: int
    price: str
    authors: List[Optional[str]] = field(default_factory=list)
    include_picture: List[bool] = field(default_factory=list)
    location: str = ""
    paper_city: str = "Sharn"
    paper_setting: str = "Eberron"
    full_header: bool = False
    num_cols: int = 3
    big_headline_size: int = 50

    def __post_init__(self):
        num_sources = len(self.source_files)
        if len(self.include_picture) < num_sources:
            self.include_picture = [False] * num_sources
        while len(self.authors) < num_sources:
            self.authors.append(None)


class PaperAI:
    """Get ChatGPT-generated articles from prompts."""

    def __init__(self, api_key: str) -> None:
        openai.api_key = api_key
        # Load the Jinja template
        self.template = JINJA_ENV.get_template("prompt.txt")
        # Format the template with the data

    def query(
        self,
        article_subject: str,
        paper_title: str = "The Sharn Inquisitive",
        paper_city: str = "Sharn",
        paper_setting: str = "Eberron",
        author: Optional[str] = None,
        include_picture: bool = False,
    ) -> Article:
        data = {
            "subject": article_subject,
            "title": paper_title,
            "city": paper_city,
            "setting": paper_setting,
            "include_picture": include_picture,
        }
        prompt = self.template.render(data)

        # Define the parameters for the GPT-3 request
        params = {
            "model": "text-davinci-003",
            "prompt": prompt,
            "temperature": 0.4,
            "max_tokens": 3000,
        }

        # Send the request to GPT-3 and print the response
        response = openai.Completion.create(**params)
        print(response)
        return self.parse_response(response.choices[0].text, author)

    @staticmethod
    def parse_response(response: str, author: Optional[str] = None) -> Article:
        """Format an OpenAI response."""
        title_patt = r"Title: (?P<title>.+)"
        picture_patt = r"Picture: (?P<picture_description>.+)"
        quotes_patt = r"\"([^\"]+)\""

        print(response)

        # Replace quotes with the proper format
        response = re.sub(quotes_patt, r"``\g<1>''", response)

        title_match = re.search(title_patt, response)
        if not title_match:
            raise ValueError("Could not find title!")
        else:
            title = title_match.group("title")

        response = re.sub(title_patt, "", response)

        picture_match = re.search(picture_patt, response)
        if picture_match:
            picture_description = picture_match.group("picture_description")

            article_texts = re.split(picture_patt, response)
            # The second element contains the picture description, which we overwrite
            del article_texts[1]

            # TODO: Generate picture!
            raise NotImplementedError()
            picture_path = Path()
            article_blocks = [
                ArticleBlock(article_texts[0]),
                ArticleBlock(None, picture_path),
            ]

        else:
            article_blocks = [ArticleBlock(response)]

        return Article(title, article_blocks, author)

    def get_paper(self, config: PaperConfig):
        """Generate a paper from a list of prompt files and authors."""
        articles = []
        for source, author, include_picture in zip(
            config.source_files, config.authors, config.include_picture
        ):
            subject = source.read_text()
            articles.append(
                self.query(
                    subject,
                    config.title,
                    config.paper_city,
                    config.paper_setting,
                    author,
                    include_picture,
                )
            )

        return Newspaper(
            config.title,
            config.date,
            config.volume,
            config.issue,
            config.price,
            articles,
            config.location,
            config.full_header,
            config.num_cols,
            config.big_headline_size,
        )


if __name__ == "__main__":
    inputs = [Path("example_prompt_1.txt"), Path("example_prompt_2.txt"), Path("example_prompt_3.txt")]
    config = PaperConfig(
        inputs,
        "The Sharn Inquisitive",
        "2 Olarune 998 YK",
        4,
        6,
        "1 CP",
        [None, None, "Mabel Sneaker"]
    )
    paper_ai = PaperAI(Path("OPENAI-API.txt").read_text())
    paper = paper_ai.get_paper(config)

    example_output = Path("example_paper.tex")
    example_output.write_text(paper.render())
