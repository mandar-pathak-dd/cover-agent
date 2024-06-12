from jinja2 import Template
import json


class ReportGenerator:
    # Enhanced HTML template with additional styling
    HTML_TEMPLATE = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Test Results</title>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.23.0/themes/prism-okaidia.min.css" rel="stylesheet" />
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 20px;
            }
            table {
                border-collapse: collapse;
                width: 100%;
                box-shadow: 0 2px 3px rgba(0,0,0,0.1);
            }
            th, td {
                border: 1px solid #ddd;
                text-align: left;
                padding: 8px;
            }
            th {
                background-color: #f2f2f2;
            }
            tr:nth-child(even) {
                background-color: #f9f9f9;
            }
            .status-pass {
                color: green;
            }
            .status-fail {
                color: red;
            }
            pre {
                background-color: #000000 !important;
                color: #ffffff !important;
                padding: 5px;
                border-radius: 5px;
            }
        </style>
    </head>
    <body>
        <table>
            <tr>
                <th>Status</th>
                <th>Reason</th>
                <th>Exit Code</th>
                <th>Test</th>
                <th>StdOut</th>
                <th>StdErr</th>
            </tr>
            {% for result in results %}
            <tr>
                <td class="status-{{ result.status }}">{{ result.status }}</td>
                <td>{{ result.reason }}</td>
                <td>{{ result.exit_code }}</td>
                <td>{% if result.test %}<pre><code class="language-python">{{ result.test }}</code></pre>{% else %}&nbsp;{% endif %}</td>
                <td>{% if result.stdout %}<pre><code class="language-shell">{{ result.stdout }}</code></pre>{% else %}&nbsp;{% endif %}</td>
                <td>{% if result.stderr %}<pre><code class="language-shell">{{ result.stderr }}</code></pre>{% else %}&nbsp;{% endif %}</td>
            </tr>
            {% endfor %}
        </table>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.23.0/prism.min.js"></script>
    </body>
    </html>
    """

    @classmethod
    def generate_report(cls, results, file_path):
        """
        Renders the HTML report with given results and writes to a file.

        :param results: List of dictionaries with test results.
        :param file_path: Path to the HTML file where the report will be written.
        """

        template = Template(cls.HTML_TEMPLATE)
        for result in results:
            #result['test'] = json.dumps(result['test'], indent=4)
            result['test'] = f"""
Test Behavior: {result['test']['test_behavior']}\n
Lines to Cover: {result['test']['lines_to_cover']}\n
Test Name: {result['test']['test_name']}\n
Test Code:\n{result['test']['test_code']}\n
            """.strip()
        html_content = template.render(results=results)

        with open(file_path, "w") as file:
            file.write(html_content)
