"""Self-contained HTML report renderer.

Emits a single .html file with inline SVG charts (matplotlib SVG backend), no
external CDN/JS. Dark-themed, mirrors the markdown reporter's coverage.
"""

from __future__ import annotations

import html as html_lib
import io
import os
from datetime import datetime

import matplotlib
matplotlib.use('Agg', force=True)
from matplotlib.figure import Figure
from matplotlib.backends.backend_svg import FigureCanvasSVG

from .base import BaseReporter


_PALETTE = ['#60a5fa', '#34d399', '#f472b6', '#fbbf24', '#a78bfa',
            '#fb7185', '#22d3ee', '#facc15']


def _esc(value) -> str:
    return html_lib.escape(str(value), quote=True)


def _fmt_int(n: int | float) -> str:
    try:
        return f"{int(n):,}"
    except (TypeError, ValueError):
        return str(n)


def _render_svg(fig: Figure) -> str:
    """Render a Figure to inline SVG markup (no XML prolog so it embeds cleanly)."""
    buf = io.BytesIO()
    canvas = FigureCanvasSVG(fig)
    canvas.print_svg(buf)
    raw = buf.getvalue().decode('utf-8')
    # Strip XML declaration and DOCTYPE so the SVG drops straight into <body>.
    if raw.startswith('<?xml'):
        raw = raw.split('?>', 1)[1]
    if '<!DOCTYPE' in raw:
        raw = raw.split('>', 1)[1] if raw.lstrip().startswith('<!DOCTYPE') else raw
    return raw.strip()


class HTMLReporter(BaseReporter):
    def __init__(self, *args, **kwargs):
        self.project_name = kwargs.pop('project_name', 'Code Analysis')
        super().__init__(*args, **kwargs)

    def generate_report(self, output_path: str) -> None:
        pie_svg = self._render_language_pie()
        composition_svg = self._render_composition_bars()

        body_parts: list[str] = []
        body_parts.append(self._render_header())
        body_parts.append(self._render_summary())
        body_parts.append(self._render_chart_block('Language distribution', pie_svg))
        body_parts.append(self._render_chart_block('Code composition by language', composition_svg))
        body_parts.append(self._render_language_sections())

        document = self._wrap('\n'.join(body_parts))
        with open(output_path, 'w', encoding='utf-8') as fh:
            fh.write(document)

    def _render_header(self) -> str:
        generated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return (
            '<header class="hero">'
            f'<h1>{_esc(self.project_name)}</h1>'
            '<p class="subtitle">Code analysis report</p>'
            f'<p class="meta">Generated {_esc(generated)}</p>'
            '</header>'
        )

    def _render_summary(self) -> str:
        rows: list[tuple[str, str, str]] = [
            ('Total directories', _fmt_int(self.total_dirs), ''),
            ('Total files', _fmt_int(self.total_files), ''),
            ('Total lines', _fmt_int(self.total_lines), '100%'),
        ]

        if self.total_lines > 0:
            rows.extend([
                ('└─ Code lines',
                 _fmt_int(self.total_code_lines),
                 f"{(self.total_code_lines / self.total_lines) * 100:.1f}%"),
                ('└─ Comment lines',
                 _fmt_int(self.total_comment_lines),
                 f"{(self.total_comment_lines / self.total_lines) * 100:.1f}%"),
                ('└─ Blank lines',
                 _fmt_int(self.total_blank_lines),
                 f"{(self.total_blank_lines / self.total_lines) * 100:.1f}%"),
            ])

        rows.extend([
            ('Total characters', _fmt_int(self.total_characters), ''),
            ('Total words', _fmt_int(self.total_words), ''),
            ('Functions', _fmt_int(self.total_functions), ''),
            ('Classes', _fmt_int(self.total_classes), ''),
            ('TODOs', _fmt_int(self.total_todos), ''),
            ('Imports', _fmt_int(self.total_imports), ''),
        ])

        if self.total_files > 0:
            rows.append(('Avg lines/file', f"{self.total_lines / self.total_files:.1f}", ''))
            rows.append(('Avg code lines/file', f"{self.total_code_lines / self.total_files:.1f}", ''))

        body_rows = ''.join(
            f'<tr><td>{_esc(metric)}</td><td class="num">{_esc(value)}</td><td class="num muted">{_esc(pct)}</td></tr>'
            for metric, value, pct in rows
        )
        return (
            '<section class="card">'
            '<h2>Summary statistics</h2>'
            '<table>'
            '<thead><tr><th>Metric</th><th class="num">Value</th><th class="num">%</th></tr></thead>'
            f'<tbody>{body_rows}</tbody>'
            '</table>'
            '</section>'
        )

    def _render_chart_block(self, title: str, svg: str) -> str:
        return (
            '<section class="card">'
            f'<h2>{_esc(title)}</h2>'
            f'<div class="chart">{svg}</div>'
            '</section>'
        )

    def _render_language_sections(self) -> str:
        if not self.metrics_by_language:
            return ''

        cards: list[str] = ['<section class="card"><h2>Detailed statistics by language</h2>']

        for language, metrics in self.metrics_by_language.items():
            stats = self.language_stats.get(language, {})
            rows: list[tuple[str, str]] = [
                ('Total files', _fmt_int(stats.get('total_files', 0))),
                ('Avg lines/file', f"{stats.get('avg_lines_per_file', 0):.1f}"),
                ('Median lines/file', f"{stats.get('median_lines_per_file', 0):.1f}"),
            ]

            if language in self.largest_line_files:
                file_path, line_count = self.largest_line_files[language]
                rows.append(('Largest file', os.path.basename(str(file_path))))
                rows.append(('Largest file lines', _fmt_int(line_count)))

            rows.extend([
                ('Total lines', _fmt_int(metrics.total_lines)),
                ('Code lines', _fmt_int(metrics.code_lines)),
                ('Comment lines', _fmt_int(metrics.comment_lines)),
                ('Blank lines', _fmt_int(metrics.blank_lines)),
                ('Characters', _fmt_int(metrics.characters)),
                ('Words', _fmt_int(metrics.words)),
            ])

            if metrics.total_lines > 0:
                denom = metrics.total_lines - metrics.blank_lines
                avg_line_len = metrics.characters / denom if denom > 0 else 0
                rows.append(('Avg line length', f"{avg_line_len:.2f}"))

            rows.extend([
                ('Functions', _fmt_int(metrics.functions)),
                ('Classes', _fmt_int(metrics.classes)),
                ('TODOs', _fmt_int(metrics.todos)),
                ('Imports', _fmt_int(metrics.imports)),
            ])

            if language == 'Python':
                rows.extend([
                    ('Decorators', _fmt_int(getattr(metrics, 'decorators', 0))),
                    ('List comprehensions', _fmt_int(getattr(metrics, 'list_comprehensions', 0))),
                    ('Lambda functions', _fmt_int(getattr(metrics, 'lambda_functions', 0))),
                    ('f-strings', _fmt_int(getattr(metrics, 'f_strings', 0))),
                ])
            elif language in {'HTML', 'CSS'}:
                rows.extend([
                    ('Elements', _fmt_int(getattr(metrics, 'elements', 0))),
                    ('Attributes', _fmt_int(getattr(metrics, 'attributes', 0))),
                    ('Media queries', _fmt_int(getattr(metrics, 'media_queries', 0))),
                    ('Selectors', _fmt_int(getattr(metrics, 'selectors', 0))),
                ])

            row_html = ''.join(
                f'<tr><td>{_esc(k)}</td><td class="num">{_esc(v)}</td></tr>' for k, v in rows
            )
            cards.append(
                f'<details open class="lang-section"><summary>{_esc(language)}</summary>'
                '<table>'
                '<thead><tr><th>Metric</th><th class="num">Value</th></tr></thead>'
                f'<tbody>{row_html}</tbody>'
                '</table>'
                '</details>'
            )

        cards.append('</section>')
        return ''.join(cards)

    def _render_language_pie(self) -> str:
        items = sorted(
            ((lang, m.total_lines) for lang, m in self.metrics_by_language.items()),
            key=lambda x: x[1],
            reverse=True,
        )
        labels = [name for name, _ in items]
        values = [count for _, count in items]

        fig = Figure(figsize=(8, 5), facecolor='#0f172a')
        ax = fig.add_subplot(111)
        ax.set_facecolor('#0f172a')

        if values and sum(values) > 0:
            wedge_colors = (_PALETTE * ((len(values) // len(_PALETTE)) + 1))[:len(values)]
            wedges, _texts, autotexts = ax.pie(
                values,
                colors=wedge_colors,
                autopct='%1.1f%%',
                pctdistance=0.75,
                wedgeprops=dict(width=0.55, edgecolor='#0f172a'),
                textprops={'fontsize': 11, 'color': '#e2e8f0'},
            )
            for t in autotexts:
                t.set_color('#0f172a')
                t.set_fontweight('bold')
            ax.legend(
                wedges,
                labels,
                title='Languages',
                loc='center left',
                bbox_to_anchor=(1.0, 0.5),
                facecolor='#1e293b',
                edgecolor='#334155',
                labelcolor='#e2e8f0',
                title_fontsize=11,
                fontsize=10,
            )
            leg_title = ax.get_legend().get_title()
            if leg_title is not None:
                leg_title.set_color('#e2e8f0')
            ax.set_title('Lines of code by language', color='#e2e8f0', pad=14, fontsize=13)
            ax.axis('equal')
        else:
            ax.text(0.5, 0.5, 'No language data', ha='center', va='center',
                    fontsize=14, color='#94a3b8')
            ax.set_axis_off()

        fig.tight_layout()
        return _render_svg(fig)

    def _render_composition_bars(self) -> str:
        languages = sorted(
            self.metrics_by_language.keys(),
            key=lambda l: self.metrics_by_language[l].total_lines,
            reverse=True,
        )

        fig = Figure(figsize=(10, 5.5), facecolor='#0f172a')
        ax = fig.add_subplot(111)
        ax.set_facecolor('#0f172a')

        if languages:
            code_lines = [self.metrics_by_language[l].code_lines for l in languages]
            comment_lines = [self.metrics_by_language[l].comment_lines for l in languages]
            blank_lines = [self.metrics_by_language[l].blank_lines for l in languages]

            x = list(range(len(languages)))
            width = 0.27
            ax.bar([i - width for i in x], code_lines, width, label='Code', color='#34d399')
            ax.bar(x, comment_lines, width, label='Comments', color='#60a5fa')
            ax.bar([i + width for i in x], blank_lines, width, label='Blank', color='#a78bfa')

            ax.set_xticks(x)
            ax.set_xticklabels(languages, rotation=35, ha='right', color='#e2e8f0')
            ax.set_ylabel('Lines', color='#e2e8f0')
            ax.set_title('Code composition by language', color='#e2e8f0', pad=14, fontsize=13)
            ax.tick_params(axis='y', colors='#94a3b8')
            ax.tick_params(axis='x', colors='#e2e8f0')
            for spine in ax.spines.values():
                spine.set_color('#334155')
            ax.grid(True, axis='y', linestyle='--', alpha=0.25, color='#475569')
            ax.set_axisbelow(True)
            legend = ax.legend(
                facecolor='#1e293b',
                edgecolor='#334155',
                labelcolor='#e2e8f0',
            )
            for text in legend.get_texts():
                text.set_color('#e2e8f0')
        else:
            ax.text(0.5, 0.5, 'No language data', ha='center', va='center',
                    fontsize=14, color='#94a3b8')
            ax.set_axis_off()

        fig.tight_layout()
        return _render_svg(fig)

    def _wrap(self, body: str) -> str:
        return (
            '<!DOCTYPE html>\n'
            '<html lang="en">\n'
            '<head>\n'
            '<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            f'<title>{_esc(self.project_name)} – Code Counter report</title>\n'
            '<style>\n' + _CSS + '\n</style>\n'
            '</head>\n'
            '<body>\n'
            '<main class="container">\n'
            f'{body}\n'
            '<footer class="footer">Built with Code Counter.</footer>\n'
            '</main>\n'
            '</body>\n'
            '</html>\n'
        )


_CSS = """\
:root {
  --bg: #0f172a;
  --card: #1e293b;
  --card-border: #334155;
  --text: #e2e8f0;
  --muted: #94a3b8;
  --accent: #60a5fa;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: var(--bg); color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue",
               Arial, sans-serif;
  line-height: 1.5;
}
.container { max-width: 1080px; margin: 0 auto; padding: 32px 24px 80px; }
.hero { padding: 32px 0 8px; border-bottom: 1px solid var(--card-border); margin-bottom: 24px; }
.hero h1 { margin: 0 0 4px; font-size: 32px; letter-spacing: -0.01em; }
.subtitle { margin: 0; color: var(--accent); font-weight: 500; }
.meta { margin: 8px 0 0; color: var(--muted); font-size: 13px; }
.card { background: var(--card); border: 1px solid var(--card-border);
  border-radius: 12px; padding: 24px; margin: 16px 0; }
.card h2 { margin: 0 0 16px; font-size: 18px; color: var(--text); }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #334155; }
thead th { font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em;
  color: var(--muted); font-weight: 600; background: rgba(15, 23, 42, 0.4); }
tbody tr:last-child td { border-bottom: none; }
tbody tr:hover { background: rgba(96, 165, 250, 0.04); }
.num { text-align: right; font-variant-numeric: tabular-nums; }
.muted { color: var(--muted); }
.chart { display: flex; justify-content: center; padding: 8px 0; }
.chart svg { max-width: 100%; height: auto; }
.lang-section { margin: 16px 0; border: 1px solid var(--card-border); border-radius: 8px;
  background: rgba(15, 23, 42, 0.5); }
.lang-section > summary { cursor: pointer; padding: 12px 16px; font-weight: 600;
  font-size: 15px; color: var(--text); list-style: none; }
.lang-section > summary::-webkit-details-marker { display: none; }
.lang-section > summary::before { content: "▸"; display: inline-block; width: 14px;
  color: var(--accent); transition: transform 0.15s ease; }
.lang-section[open] > summary::before { transform: rotate(90deg); }
.lang-section table { padding: 0 16px 16px; }
.lang-section[open] table { border-top: 1px solid var(--card-border); }
.footer { margin-top: 32px; text-align: center; color: var(--muted); font-size: 12px; }
"""
