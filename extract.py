import pandas as pd
import json

df = pd.read_excel('Ткани база.xlsx')
data = {
    'columns': df.columns.tolist(),
    'sample': df.head(5).to_dict('records')
}
with open('excel_data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print("done")
