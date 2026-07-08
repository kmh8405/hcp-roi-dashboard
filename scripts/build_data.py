import csv, json
from collections import defaultdict

UP = '/sessions/amazing-ecstatic-bell/mnt/uploads/'

# ---- canonical product mapping ----
def canon(brand):
    b = brand.lower()
    if 'entresto' in b: return 'ENTRESTO'
    if 'cosentyx' in b: return 'COSENTYX'
    if 'lucentis' in b: return 'LUCENTIS'
    return brand.upper()

CANON_DISPLAY = {'ENTRESTO':'Entresto', 'COSENTYX':'Cosentyx', 'LUCENTIS':'Lucentis'}

# ---- load Part D ----
# per NPI per canonical product: sum claims/cost ; also keep doc meta
rx = defaultdict(lambda: defaultdict(lambda: {'clms':0.0,'cost':0.0,'day_supply':0.0}))
doc_meta = {}
with open(UP+'part_d_prescriber.csv') as f:
    r = csv.DictReader(f)
    for row in r:
        npi = row['Prscrbr_NPI']
        prod = canon(row['Brnd_Name'])
        clms = float(row['Tot_Clms'] or 0)
        cost = float(row['Tot_Drug_Cst'] or 0)
        rx[npi][prod]['clms'] += clms
        rx[npi][prod]['cost'] += cost
        doc_meta[npi] = {
            'name': f"{row['Prscrbr_First_Name']} {row['Prscrbr_Last_Org_Name']}",
            'city': row['Prscrbr_City'],
            'state': row['Prscrbr_State_Abrvtn'],
            'specialty': row['Prscrbr_Type'],
        }

# ---- load Open Payments ----
# per NPI per canonical product: sum payment amt/count ; also payment_nature breakdown (not used in P0 but computed)
pay = defaultdict(lambda: defaultdict(lambda: {'amt':0.0,'cnt':0}))
pay_any = defaultdict(lambda: {'amt':0.0,'cnt':0})
op_meta = {}
with open(UP+'open_payments.csv') as f:
    r = csv.DictReader(f)
    for row in r:
        npi = row['covered_recipient_npi']
        amt = float(row['payment_amount_usd'] or 0)
        products_in_row = set()
        for k in ['product_1','product_2','product_3','product_4','product_5']:
            p = row[k]
            if p:
                products_in_row.add(canon(p))
        pay_any[npi]['amt'] += amt
        pay_any[npi]['cnt'] += 1
        for p in products_in_row:
            pay[npi][p]['amt'] += amt
            pay[npi][p]['cnt'] += 1
        if npi not in op_meta:
            op_meta[npi] = {
                'name': f"{row['recipient_first_name']} {row['recipient_last_name']}",
                'city': row['recipient_city'],
                'state': row['recipient_state'],
                'specialty': (row['recipient_specialty'].split('|')[0] if row['recipient_specialty'] else ''),
            }

PRODUCTS = ['ENTRESTO','COSENTYX','LUCENTIS']

# ---- product-level summary (ROI) ----
product_summary = []
for p in PRODUCTS:
    rx_cost = sum(v[p]['cost'] for v in rx.values() if p in v)
    rx_clms = sum(v[p]['clms'] for v in rx.values() if p in v)
    rx_prescribers = sum(1 for v in rx.values() if p in v)
    pay_amt = sum(v[p]['amt'] for v in pay.values() if p in v)
    pay_cnt = sum(v[p]['cnt'] for v in pay.values() if p in v)
    pay_recipients = sum(1 for v in pay.values() if p in v)
    roi = (rx_cost / pay_amt) if pay_amt > 0 else None
    product_summary.append({
        'product': p,
        'display': CANON_DISPLAY[p],
        'rxCost': round(rx_cost,2),
        'rxClaims': round(rx_clms,1),
        'rxPrescribers': rx_prescribers,
        'paymentAmount': round(pay_amt,2),
        'paymentRecords': pay_cnt,
        'paymentRecipients': pay_recipients,
        'roi': round(roi,2) if roi else None,
        'hasPaymentData': pay_amt > 0,
    })

# ---- overall (all 3 products combined at NPI level) ----
overall_rx_cost = defaultdict(float)
overall_rx_clms = defaultdict(float)
for npi, prods in rx.items():
    for p in PRODUCTS:
        if p in prods:
            overall_rx_cost[npi] += prods[p]['cost']
            overall_rx_clms[npi] += prods[p]['clms']

overall_total_rx = sum(overall_rx_cost.values())
overall_total_pay = sum(v['amt'] for npi,v in pay_any.items() if npi in overall_rx_cost)  # payments to matched-domain NPIs only (any product)
overall_total_pay_all_npi = sum(v['amt'] for v in pay_any.values())

# ---- paid vs unpaid, per product + overall ----
def paid_vs_unpaid(product=None):
    paid_cost, paid_clms, paid_n = 0.0, 0.0, 0
    unpaid_cost, unpaid_clms, unpaid_n = 0.0, 0.0, 0
    for npi, prods in rx.items():
        if product:
            if product not in prods: continue
            cost = prods[product]['cost']
            clms = prods[product]['clms']
            is_paid = product in pay.get(npi, {})
        else:
            if npi not in overall_rx_cost: continue
            cost = overall_rx_cost[npi]
            clms = overall_rx_clms[npi]
            is_paid = npi in pay_any
        if is_paid:
            paid_cost += cost; paid_clms += clms; paid_n += 1
        else:
            unpaid_cost += cost; unpaid_clms += clms; unpaid_n += 1
    return {
        'paid': {'n': paid_n, 'avgCost': round(paid_cost/paid_n,2) if paid_n else 0, 'avgClaims': round(paid_clms/paid_n,1) if paid_n else 0, 'totalCost': round(paid_cost,2)},
        'unpaid': {'n': unpaid_n, 'avgCost': round(unpaid_cost/unpaid_n,2) if unpaid_n else 0, 'avgClaims': round(unpaid_clms/unpaid_n,1) if unpaid_n else 0, 'totalCost': round(unpaid_cost,2)},
    }

paid_unpaid = {'ALL': paid_vs_unpaid(None)}
for p in PRODUCTS:
    paid_unpaid[p] = paid_vs_unpaid(p)

# ---- top HCP lists ----
def top_hcp(product=None, n=25):
    rows = []
    if product:
        for npi, prods in rx.items():
            if product not in prods: continue
            cost = prods[product]['cost']; clms = prods[product]['clms']
            payamt = pay.get(npi, {}).get(product, {}).get('amt', 0.0)
            meta = doc_meta.get(npi, {})
            rows.append({
                'npi': npi, 'name': meta.get('name','').strip(), 'city': meta.get('city',''),
                'specialty': meta.get('specialty',''), 'rxCost': round(cost,2), 'rxClaims': round(clms,1),
                'paymentAmount': round(payamt,2), 'matched': payamt > 0,
            })
    else:
        for npi, cost in overall_rx_cost.items():
            clms = overall_rx_clms[npi]
            payamt = pay_any.get(npi, {}).get('amt', 0.0)
            meta = doc_meta.get(npi, {})
            rows.append({
                'npi': npi, 'name': meta.get('name','').strip(), 'city': meta.get('city',''),
                'specialty': meta.get('specialty',''), 'rxCost': round(cost,2), 'rxClaims': round(clms,1),
                'paymentAmount': round(payamt,2), 'matched': payamt > 0,
            })
    rows.sort(key=lambda x: -x['rxCost'])
    return rows[:n]

top_hcp_lists = {'ALL': top_hcp(None)}
for p in PRODUCTS:
    top_hcp_lists[p] = top_hcp(p)

# ---- matched / unmatched NPI counts (overall, for footnote) ----
pd_npis = set(rx.keys())
op_npis = set(pay_any.keys())
matched_count = len(pd_npis & op_npis)

data = {
    'meta': {
        'generatedNote': 'Part D (CA, 5 brands) x Open Payments (CA-centric, 2022, Novartis) 결합 분석',
        'partDPrescriberCount': len(pd_npis),
        'openPaymentsRecipientCount': len(op_npis),
        'matchedNpiCount': matched_count,
        'overallTotalRxCost': round(overall_total_rx,2),
        'overallTotalPaymentAllProducts': round(overall_total_pay_all_npi,2),
    },
    'products': product_summary,
    'paidVsUnpaid': paid_unpaid,
    'topHcp': top_hcp_lists,
}

with open('/sessions/amazing-ecstatic-bell/mnt/outputs/dashboard/data.json','w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(json.dumps(data['meta'], indent=2, ensure_ascii=False))
print()
print(json.dumps(data['products'], indent=2, ensure_ascii=False))
print()
print(json.dumps(data['paidVsUnpaid'], indent=2, ensure_ascii=False))
