import pandas as pd


df = pd.read_excel('projects.xlsx') 
df.to_csv('projects.xlsx - Sheet1.csv', index=False, encoding='utf-8')
df = pd.read_excel('project_members.xlsx') 
df.to_csv('project_members.xlsx - Sheet1.csv', index=False, encoding='utf-8')

print("文件已成功转换为 projects.xlsx - Sheet1.csv")
