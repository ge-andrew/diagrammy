from django.shortcuts import render
from django.http import HttpResponse
import matplotlib.pyplot as plt
import io
import base64
import json
import re
import numpy as np
from openai import OpenAI
import pandas as pd
from blockdiag import parser, builder, drawer
import os
from django.conf import settings

def landing(request):
    return render(request, "core/landing.html")

def process_text(request):
    if request.method == 'POST':
        API_KEY = settings.OPENAI_API_KEY
        client = OpenAI(api_key=API_KEY)

        PROMPT_PATH = os.path.join(settings.BASE_DIR, 'core', 'static', 'prompt.json')

        with open(PROMPT_PATH, "r", encoding="utf-8") as prompt:
            conversation = json.load(prompt)

        input_notes = request.POST['user_input']
        conversation['messages'].append({
            "role":"user",
            "content":input_notes
        })

        COMPLETION = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=conversation['messages'],
            response_format={"type": "json_object"}
        )

        json_data = COMPLETION.to_json()

        chat_completion_dict = json.loads(json_data)

        response = json.loads(chat_completion_dict["choices"][0]["message"]["content"])

        graph_type = response['graph']

        try:
            if graph_type == "flowchart":
                edges = response['edges']
                diagram_code = "blockdiag {\n"
                for edge in edges:
                    diagram_code += f"'{edge[0]}' -> '{edge[1]}';\n"
                diagram_code += "}"
                tree = parser.parse_string(diagram_code)
                diagram = builder.ScreenNodeBuilder.build(tree)
                
                with io.BytesIO() as buf:
                    draw = drawer.DiagramDraw('PNG', diagram, filename=buf)
                    draw.draw()
                    draw.save()
                    
                    buf.seek(0)
                    
                    image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
                    image_url = f"data:image/png;base64, {image_base64}"
                    return render(request, 'core/landing.html', {'image_url':image_url})
                
            elif graph_type == "table":
                columns = response["columns"]
                df = {}
                for item in columns:
                    df.update({item[0]:item[1:]})
                df = pd.DataFrame(df)
                _, ax = plt.subplots(figsize=(10, 6)) 
                ax.axis('tight')
                ax.axis('off')
                table = ax.table(cellText=df.values, colLabels=df.columns, cellLoc='center', loc='center')
                table.auto_set_font_size(False)
                table.set_fontsize(10)
                table.auto_set_column_width(col=list(range(len(df.columns))))
                
                with io.BytesIO() as buf:
                    plt.savefig(buf, format='png')
                    plt.close()
                    buf.seek(0)

                    image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
                    image_url = f"data:image/png;base64, {image_base64}"

                    return render(request, 'core/landing.html', {'image_url':image_url})

            elif graph_type == "pie chart":
                
                sections = response["percentages"]
                _, ax = plt.subplots()
                percentages = []
                labels = []
                for percentage, label in sections:
                    percentages.append(percentage)
                    labels.append(label)
                ax.pie(percentages, labels=labels, autopct='%1.1f%%')

                with io.BytesIO() as buf:
                    plt.savefig(buf, format='png')
                    plt.close()
                    buf.seek(0)

                    image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
                    image_url = f"data:image/png;base64, {image_base64}"

                    return render(request, 'core/landing.html', {'image_url':image_url})

            elif graph_type == "bar chart":

                bars = response["bars"]
                values = [i[0] for i in bars]
                categories = [i[1] for i in bars]
                plt.bar(categories, values)
                plt.xlabel(response["x Axis"])
                plt.ylabel(response["y Axis"])
                
                with io.BytesIO() as buf:
                    plt.savefig(buf, format='png')
                    plt.close()
                    buf.seek(0)

                    image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
                    image_url = f"data:image/png;base64, {image_base64}"

                    return render(request, 'core/landing.html', {'image_url':image_url})
            elif graph_type == "timeline":

                DATETIME_PATTERNS = [
                    r'^\d{4}$',
                    r'^\d{4}-\d{1,2}$',
                    r'^\d{4}-\d{1,2}-\d{1,2}$'
                ]

                events = response["events"]
                dates = []
                labels = []
                for date, label in events:
                    if re.match(DATETIME_PATTERNS[0], date):
                        dates.append(float(date))
                        labels.append(f"{date}: {label}")
                    elif re.match(DATETIME_PATTERNS[1], date):
                        dates.append(float(date[0:4]) + float(date[5:7])/12.0)
                        labels.append(f"{date[0:4]}-{date[5:7]}: {label}")
                    elif re.match(DATETIME_PATTERNS[2], date):
                        dates.append(float(date[0:4]) + float(date[5:7]
                                                            )/12.0 + float(date[8:10])/365.0)
                        labels.append(f"{date[0:4]}-{date[5:7]}-{date[8:10]}: {label}")
                    else:
                        print(f"Timeline graph error: unexpected date format: {date}")
                _, ax = plt.subplots(figsize=(15, 4), constrained_layout=True)
                _ = ax.set_ylim(-2, 1.75)
                _ = ax.set_xlim(min(dates), max(dates))
                _ = ax.axhline(0, xmin=0.05, xmax=0.95, c='deeppink', zorder=1)
                _ = ax.scatter(dates, np.zeros(len(dates)),
                            s=120, c='palevioletred', zorder=2)
                _ = ax.scatter(dates, np.zeros(len(dates)),
                            s=30, c='darkmagenta', zorder=3)
                label_offsets = np.zeros(len(dates))
                label_offsets[::2] = 0.35
                label_offsets[1::2] = -0.7
                for i, (l, d) in enumerate(zip(labels, dates)):
                    _ = ax.text(d, label_offsets[i], f"{l}", ha='center', fontfamily='serif', fontweight='bold', color='royalblue', fontsize=12)
                stems = np.zeros(len(dates))
                stems[::2] = 0.3
                stems[1::2] = -0.3
                markerline, stemline, _ = ax.stem(dates, stems)
                _ = plt.setp(markerline, marker=',', color='darkmagenta')
                _ = plt.setp(stemline, color='darkmagenta')
                # hide lines around chart
                for spine in ["left", "top", "right", "bottom"]:
                    _ = ax.spines[spine].set_visible(False)
                # hide tick labels
                _ = ax.set_xticks([])
                _ = ax.set_yticks([])

                with io.BytesIO() as buf:
                    plt.savefig(buf, format='png')
                    plt.close()
                    buf.seek(0)

                    image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
                    image_url = f"data:image/png;base64, {image_base64}"

                    return render(request, 'core/landing.html', {'image_url':image_url})
        except Exception as e:
            print(f"Error: {e}")
            print(f"GPT Response: {response}")
            return HttpResponse(f"An error occured: {e}\n{response}")

        ERROR_TEXT = "An Error Occurred. Try again, or try a different text input."
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, ERROR_TEXT, fontsize=12, ha='center')
        ax.axis('off')
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        buf.seek(0)
        plt.close(fig)

        image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        image_url = f"data:image/png;base64, {image_base64}"

        return render(request, 'core/landing.html', {'image_url':image_url})
    return HttpResponse("Invalid Request")

def about(request):
    return render(request, "core/about.html")
