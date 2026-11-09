with open('web/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

target = """    /* 1. Flow Steps Grid (4 flows: Inflow, Spend, Refund, Gas) */
    .flow-steps-grid {
      display: grid !important;
      grid-template-columns: repeat(4, 1fr) !important;
      gap: 16px !important;
      align-items: stretch !important;
    }

    @media (max-width: 1100px) {
      .flow-steps-grid {
        grid-template-columns: repeat(2, 1fr) !important;
        /* 2 trên 2 dưới */
      }
    }

    @media (max-width: 580px) {
      .flow-steps-grid {
        grid-template-columns: 1fr !important;
      }
    }"""

replacement = """    /* 1. Flow Steps Grid (4 flows: Inflow, Spend, Refund, Gas) - Rộng rãi, không ép cột hẹp */
    .flow-steps-grid {
      display: grid !important;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)) !important;
      gap: 20px !important;
      align-items: stretch !important;
    }

    @media (max-width: 600px) {
      .flow-steps-grid {
        grid-template-columns: 1fr !important;
      }
    }"""

if target in html:
    html = html.replace(target, replacement, 1)
    with open('web/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Updated flow-steps-grid in web/index.html successfully!")
else:
    print("Target not found in web/index.html!")

