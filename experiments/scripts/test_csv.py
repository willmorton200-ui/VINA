import csv
with open('d:/VINA/wines_integrated_clean.csv', encoding='utf-8') as f:
    reader = csv.reader(f)
    next(reader)
    for row in reader:
        if 'massandra-muskat-belyy' in row[7]:
            print(row[7], '=>', row[8], '=>', row[10])
