import os
from datetime import datetime

# Use the non-interactive Agg backend explicitly. Importing pyplot lazily and
# bypassing it for the Figure/canvas API avoids the thread-unsafety of pyplot's
# global state when this reporter is invoked from concurrent FastAPI requests.
import matplotlib

matplotlib.use("Agg", force=True)
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Frame,
    Image,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .base import BaseReporter


class PDFReporter(BaseReporter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.output_dir = None
        self.styles = getSampleStyleSheet()
        self.project_name = kwargs.get("project_name", "Code Analysis")

        # Custom styles
        self.title_style = ParagraphStyle(
            "CustomTitle",
            parent=self.styles["Heading1"],
            fontSize=28,
            spaceAfter=30,
            textColor=colors.HexColor("#2c3e50"),
            alignment=1,  # Center alignment
        )

        self.subtitle_style = ParagraphStyle(
            "CustomSubtitle",
            parent=self.styles["Heading2"],
            fontSize=20,
            spaceAfter=20,
            textColor=colors.HexColor("#2c3e50"),
            alignment=1,  # Center alignment
        )

        self.heading2_style = ParagraphStyle(
            "CustomHeading2",
            parent=self.styles["Heading2"],
            fontSize=20,
            spaceBefore=30,
            spaceAfter=20,
            textColor=colors.HexColor("#2c3e50"),
            keepWithNext=True,
        )

        self.heading3_style = ParagraphStyle(
            "CustomHeading3",
            parent=self.styles["Heading3"],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=15,
            textColor=colors.HexColor("#2c3e50"),
            keepWithNext=True,
        )

        self.normal_style = ParagraphStyle(
            "CustomNormal",
            parent=self.styles["Normal"],
            fontSize=11,
            textColor=colors.HexColor("#2c3e50"),
            spaceAfter=12,
        )

        # Table style
        self.table_style = TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 11),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8f9fa")),
                ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#2c3e50")),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#dee2e6")),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.HexColor("#ffffff"), colors.HexColor("#f8f9fa")],
                ),
            ]
        )

    def generate_charts(self) -> tuple[str, str]:
        """Generate charts for the PDF report (thread-safe; no global pyplot)."""
        palette = [
            "#2ecc71",
            "#3498db",
            "#9b59b6",
            "#f1c40f",
            "#e74c3c",
            "#1abc9c",
            "#e67e22",
            "#34495e",
        ]

        sorted_items = sorted(
            ((lang, m.total_lines) for lang, m in self.metrics_by_language.items()),
            key=lambda x: x[1],
            reverse=True,
        )
        languages = [name for name, _ in sorted_items]
        values = [count for _, count in sorted_items]

        # File names include the project name so concurrent runs sharing
        # an output_dir don't clobber each other's PNGs.
        safe = (self.project_name or "project").replace(os.sep, "_")
        pie_chart_path = os.path.join(self.output_dir, f"{safe}_language_distribution.png")
        composition_chart_path = os.path.join(self.output_dir, f"{safe}_code_composition.png")

        # Pie chart -----------------------------------------------------------
        fig = Figure(figsize=(10, 8))
        canvas = FigureCanvasAgg(fig)
        ax = fig.add_subplot(111)

        if values and sum(values) > 0:
            colors_for_wedges = (palette * ((len(values) // len(palette)) + 1))[: len(values)]
            ax.pie(
                values,
                colors=colors_for_wedges,
                autopct="%1.1f%%",
                pctdistance=0.75,
                wedgeprops=dict(width=0.7, edgecolor="white"),
                textprops={"fontsize": 12, "color": "#2c3e50"},
            )
            ax.legend(
                labels=languages,
                title="Languages",
                loc="center left",
                bbox_to_anchor=(1, 0, 0.5, 1),
                fontsize=11,
                title_fontsize=13,
            )
            ax.set_title("Distribution of Code by Language", pad=20, fontsize=16, color="#2c3e50")
            ax.axis("equal")
        else:
            ax.text(
                0.5, 0.5, "No language data", ha="center", va="center", fontsize=14, color="#7f8c8d"
            )
            ax.set_axis_off()

        fig.tight_layout()
        canvas.print_figure(pie_chart_path, dpi=200, bbox_inches="tight", facecolor="white")

        # Composition bar chart ----------------------------------------------
        fig2 = Figure(figsize=(12, 7))
        canvas2 = FigureCanvasAgg(fig2)
        ax2 = fig2.add_subplot(111)

        if languages:
            code_lines = [self.metrics_by_language[lang].code_lines for lang in languages]
            comment_lines = [self.metrics_by_language[lang].comment_lines for lang in languages]
            blank_lines = [self.metrics_by_language[lang].blank_lines for lang in languages]

            x = list(range(len(languages)))
            width = 0.25
            ax2.bar(
                [i - width for i in x], code_lines, width, label="Code", color="#2ecc71", alpha=0.8
            )
            ax2.bar(x, comment_lines, width, label="Comments", color="#3498db", alpha=0.8)
            ax2.bar(
                [i + width for i in x],
                blank_lines,
                width,
                label="Blank",
                color="#9b59b6",
                alpha=0.8,
            )
            ax2.set_xlabel("Languages", fontsize=12, color="#2c3e50", labelpad=10)
            ax2.set_ylabel("Lines", fontsize=12, color="#2c3e50", labelpad=10)
            ax2.set_title("Code Composition by Language", pad=20, fontsize=16, color="#2c3e50")
            ax2.set_xticks(x)
            ax2.set_xticklabels(languages, rotation=45, ha="right", color="#2c3e50")
            ax2.grid(True, axis="y", linestyle="--", alpha=0.3)
            ax2.legend(frameon=True, facecolor="white", framealpha=0.9, edgecolor="none")
        else:
            ax2.text(
                0.5, 0.5, "No language data", ha="center", va="center", fontsize=14, color="#7f8c8d"
            )
            ax2.set_axis_off()

        fig2.tight_layout()
        canvas2.print_figure(
            composition_chart_path, dpi=200, bbox_inches="tight", facecolor="white"
        )

        return pie_chart_path, composition_chart_path

    def add_language_section(self, story: list, language: str, metrics: dict):
        """Add a language-specific section to the PDF."""
        story.append(Paragraph(f"{language} Statistics", self.heading3_style))

        # Get language stats
        stats = self.language_stats.get(language, {})

        # Create table data
        table_data = [
            ["Metric", "Value"],
            ["Total Files", str(stats.get("total_files", 0))],
            ["Average Lines/File", f"{stats.get('avg_lines_per_file', 0):.1f}"],
            ["Median Lines/File", f"{stats.get('median_lines_per_file', 0):.1f}"],
            ["Total Lines", str(metrics.total_lines)],
            ["Code Lines", str(metrics.code_lines)],
            ["Comment Lines", str(metrics.comment_lines)],
            ["Blank Lines", str(metrics.blank_lines)],
            ["Total Characters", str(metrics.characters)],
            ["Total Words", str(metrics.words)],
        ]

        if metrics.total_lines > 0:
            avg_line_length = (
                metrics.characters / (metrics.total_lines - metrics.blank_lines)
                if (metrics.total_lines - metrics.blank_lines) > 0
                else 0
            )
            table_data.append(["Average Line Length", f"{avg_line_length:.2f}"])

        table_data.extend(
            [
                ["Functions", str(metrics.functions)],
                ["Classes", str(metrics.classes)],
                ["TODOs", str(metrics.todos)],
                ["Imports", str(metrics.imports)],
            ]
        )

        # Add language-specific metrics
        if language == "Python":
            table_data.extend(
                [
                    ["Decorators", str(getattr(metrics, "decorators", 0))],
                    ["List Comprehensions", str(getattr(metrics, "list_comprehensions", 0))],
                    ["Lambda Functions", str(getattr(metrics, "lambda_functions", 0))],
                    ["f-strings", str(getattr(metrics, "f_strings", 0))],
                ]
            )
        elif language in ["HTML", "CSS"]:
            table_data.extend(
                [
                    ["Elements", str(getattr(metrics, "elements", 0))],
                    ["Attributes", str(getattr(metrics, "attributes", 0))],
                    ["Media Queries", str(getattr(metrics, "media_queries", 0))],
                    ["Selectors", str(getattr(metrics, "selectors", 0))],
                ]
            )

        # Create and style table
        table = Table(table_data, colWidths=[200, 100])
        table.setStyle(self.table_style)
        story.append(table)
        story.append(Spacer(1, 20))

    def add_comparative_table(self, story):
        """Add a comparative table showing metrics for all languages side by side."""
        # Get all languages and sort them alphabetically
        languages = sorted(self.metrics_by_language.keys())

        # Define the metrics we want to show
        metric_groups = {
            "File Statistics": [
                (
                    "Total Files",
                    lambda lang: str(self.language_stats.get(lang, {}).get("total_files", 0)),
                ),
                (
                    "Average Lines/File",
                    lambda lang: f"{self.language_stats.get(lang, {}).get('avg_lines_per_file', 0):.1f}",
                ),
                (
                    "Median Lines/File",
                    lambda lang: f"{self.language_stats.get(lang, {}).get('median_lines_per_file', 0):.1f}",
                ),
            ],
            "Line Statistics": [
                ("Total Lines", lambda lang: str(self.metrics_by_language[lang].total_lines)),
                ("Code Lines", lambda lang: str(self.metrics_by_language[lang].code_lines)),
                ("Comment Lines", lambda lang: str(self.metrics_by_language[lang].comment_lines)),
                ("Blank Lines", lambda lang: str(self.metrics_by_language[lang].blank_lines)),
            ],
            "Content Statistics": [
                ("Total Characters", lambda lang: str(self.metrics_by_language[lang].characters)),
                ("Total Words", lambda lang: str(self.metrics_by_language[lang].words)),
                (
                    "Average Line Length",
                    lambda lang: f"{self.metrics_by_language[lang].characters / (self.metrics_by_language[lang].total_lines - self.metrics_by_language[lang].blank_lines):.1f}"
                    if self.metrics_by_language[lang].total_lines
                    - self.metrics_by_language[lang].blank_lines
                    > 0
                    else "0",
                ),
            ],
            "Code Elements": [
                ("Functions", lambda lang: str(self.metrics_by_language[lang].functions)),
                ("Classes", lambda lang: str(self.metrics_by_language[lang].classes)),
                ("TODOs", lambda lang: str(self.metrics_by_language[lang].todos)),
                ("Imports", lambda lang: str(self.metrics_by_language[lang].imports)),
            ],
        }

        # Create table data
        table_data = [["Metric"] + languages]  # Header row with "Metric" in first cell

        # Add metrics by group
        for group_name, metrics in metric_groups.items():
            # Add group header
            table_data.append([group_name] + ["" for _ in languages])
            # Add metrics for this group
            for metric_name, metric_func in metrics:
                row = [f"  {metric_name}"]  # Indent metric names
                for lang in languages:
                    row.append(metric_func(lang))
                table_data.append(row)

        # Create table style
        style = TableStyle(
            [
                # Basic styling
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),  # Left align first column
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),  # Bold header row
                ("FONTSIZE", (0, 0), (-1, -1), 8),  # Smaller font size for better fit
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#dee2e6")),
                # Header row styling
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),  # Header background
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),  # Header text color
                ("FONTSIZE", (0, 0), (-1, 0), 9),  # Slightly larger font for language names
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),  # More padding for header row
                ("TOPPADDING", (0, 0), (-1, 0), 6),
                # Metric rows styling
                ("TOPPADDING", (0, 1), (-1, -1), 4),  # Reduce padding for data rows
                ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
                # Group header styling
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8f9fa")),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.HexColor("#ffffff"), colors.HexColor("#f8f9fa")],
                ),
            ]
        )

        # Add group header styling
        group_start = 1
        for _group_name, metrics in metric_groups.items():
            style.add("BACKGROUND", (0, group_start), (-1, group_start), colors.HexColor("#e9ecef"))
            style.add("FONTNAME", (0, group_start), (-1, group_start), "Helvetica-Bold")
            style.add(
                "LINEBELOW", (0, group_start), (-1, group_start), 1, colors.HexColor("#dee2e6")
            )
            group_start += len(metrics) + 1

        # Calculate column widths based on available space
        page_width = landscape(letter)[0] - 72  # Full page width minus margins
        first_col_width = page_width * 0.2  # 20% for the metric names
        other_col_width = (page_width - first_col_width) / len(
            languages
        )  # Remaining space divided equally
        col_widths = [first_col_width] + [other_col_width] * len(languages)

        # Create and style table
        table = Table(table_data, colWidths=col_widths)
        table.setStyle(style)

        # Add to story (without duplicate heading since it's already added in generate_report)
        story.append(table)
        story.append(Spacer(1, 20))

    def generate_report(self, output_path: str) -> None:
        """Generate a PDF report."""
        # Create output directory if needed
        self.output_dir = os.path.dirname(output_path)
        os.makedirs(self.output_dir, exist_ok=True)

        # Generate charts
        pie_chart_path, composition_chart_path = self.generate_charts()

        # Define page templates with onPage handlers
        def portrait_page(canvas, doc):
            canvas.saveState()
            canvas.setPageSize(letter)
            canvas.restoreState()

        def landscape_page(canvas, doc):
            canvas.saveState()
            canvas.setPageSize(landscape(letter))
            canvas.restoreState()

        # Create page templates
        templates = [
            PageTemplate(
                id="portrait",
                pagesize=letter,
                onPage=portrait_page,
                frames=[
                    Frame(
                        36,  # left margin
                        36,  # bottom margin
                        letter[0] - 72,  # width
                        letter[1] - 72,  # height
                        leftPadding=0,
                        bottomPadding=0,
                        rightPadding=0,
                        topPadding=0,
                    )
                ],
            ),
            PageTemplate(
                id="landscape",
                pagesize=landscape(letter),
                onPage=landscape_page,
                frames=[
                    Frame(
                        36,  # left margin
                        36,  # bottom margin
                        landscape(letter)[0] - 72,  # width
                        landscape(letter)[1] - 72,  # height
                        leftPadding=0,
                        bottomPadding=0,
                        rightPadding=0,
                        topPadding=0,
                    )
                ],
            ),
        ]

        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )
        doc.addPageTemplates(templates)

        story = []

        # Project title and header
        story.append(Paragraph(self.project_name, self.title_style))
        story.append(Paragraph("Code Analysis Report", self.subtitle_style))
        story.append(
            Paragraph(
                f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", self.normal_style
            )
        )
        story.append(Spacer(1, 30))

        # Summary Statistics
        story.append(Paragraph("Summary Statistics", self.heading2_style))
        self.add_summary_table(story)

        # Set up landscape for next page
        story.append(NextPageTemplate("landscape"))
        story.append(PageBreak())

        # Language Comparison (in landscape)
        story.append(Paragraph("Language Comparison", self.heading2_style))
        self.add_comparative_table(story)

        # Set up portrait for the rest of the document
        story.append(NextPageTemplate("portrait"))
        story.append(PageBreak())

        # Charts
        story.append(Paragraph("Language Distribution", self.heading2_style))
        story.append(Image(pie_chart_path, width=7 * inch, height=5 * inch))
        story.append(Spacer(1, 30))

        story.append(Paragraph("Code Composition", self.heading2_style))
        story.append(Image(composition_chart_path, width=7.5 * inch, height=5 * inch))
        story.append(Spacer(1, 30))

        # Detailed Statistics by Language
        story.append(PageBreak())
        story.append(Paragraph("Detailed Statistics by Language", self.heading2_style))

        # Add language sections
        for language, metrics in self.metrics_by_language.items():
            self.add_language_section(story, language, metrics)

        # Build PDF
        doc.build(story)

    def add_summary_table(self, story):
        """Add summary statistics table to the PDF."""
        data = [
            ["Metric", "Value", "Percentage"],
            ["Total Directories", str(self.total_dirs), ""],
            ["Total Files", str(self.total_files), ""],
            ["Total Lines", str(self.total_lines), "100%"],
        ]

        if self.total_lines > 0:
            code_percent = f"{(self.total_code_lines / self.total_lines) * 100:.1f}%"
            comment_percent = f"{(self.total_comment_lines / self.total_lines) * 100:.1f}%"
            blank_percent = f"{(self.total_blank_lines / self.total_lines) * 100:.1f}%"

            data.extend(
                [
                    ["  ├─ Code Lines", str(self.total_code_lines), code_percent],
                    ["  ├─ Comment Lines", str(self.total_comment_lines), comment_percent],
                    ["  └─ Blank Lines", str(self.total_blank_lines), blank_percent],
                ]
            )

        data.extend(
            [
                ["Total Characters", str(self.total_characters), ""],
                ["Total Words", str(self.total_words), ""],
                ["Functions", str(self.total_functions), ""],
                ["Classes", str(self.total_classes), ""],
                ["TODOs", str(self.total_todos), ""],
                ["Imports", str(self.total_imports), ""],
            ]
        )

        if self.total_files > 0:
            avg_lines = self.total_lines / self.total_files
            avg_code_lines = self.total_code_lines / self.total_files
            data.extend(
                [
                    ["Average Lines/File", f"{avg_lines:.1f}", ""],
                    ["Average Code Lines/File", f"{avg_code_lines:.1f}", ""],
                ]
            )

        table = Table(data, colWidths=[200, 100, 100])
        table.setStyle(self.table_style)
        story.append(table)
        story.append(Spacer(1, 20))
