# Annual support in My MSP

My MSP shows an organisation's annual support agreement to organisation and
billing administrators. It combines infrastructure support, managed-app hour
bundles, automation support and custom-work support, with annual hours and
amounts per component. Monthly payment splits the annual support amount into twelve installments.
Yearly prepayment uses one invoice at the start of the contract year, with an
agreed percentage discount. All support components share the selected schedule.

The MSP records and activates agreed terms in HQ **Annual hours**. Drafts grant
no hours. Activated hours use the central support ledger and expire at the end
of the contract year. The remaining annual balance reflects ledger consumption;
implementation effort is displayed separately as a support proposal. Consultant
capacity remains agreed in days per week.

App controls continue to request support levels via real tickets. Annual app
hours and prices belong to the agreement; switching off the launcher does not
cancel that agreement. NL and EN interactive guides cover annual hours, app
support and automation proposals. Ordinary members retain tickets and app
requests but cannot view annual commercial terms.

Payment requests use the existing Payments workflow. Staff issue the accounting
invoice and record its reference before a configured live Mollie checkout can
be offered. No recurring collection or automatic accounting issuance is implied.

The annual card shows the agreed hours cap, net used hours and remaining hours
for the contract year. Calendar-month boundaries and payments never reset the
cap. Extra billable support hours require explicit approval tied to that annual
agreement. Other ledger credits do not automatically increase the annual cap.

HQ records payment frequency and yearly-prepayment discount per draft. No
default discount is assumed. Unknown prices or discounts remain unconfigured;
yearly activation requires a positive discount and a positive payable price.
The UI compares twelve monthly payments with the discounted upfront total.
Amounts use integer cents, with the rounded total discount allocated across
components so invoice lines add up exactly. The same annual hours are granted
once regardless of payment frequency. Accepted terms and invoice snapshots are
immutable; existing agreements migrate as monthly payments without a discount.
