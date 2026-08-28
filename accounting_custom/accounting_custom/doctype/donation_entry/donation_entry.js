frappe.ui.form.on('Donation Entry', {
    setup(frm) {
        frm.donor_companies = [];
        setup_donation_filters(frm);
    },

    onload(frm) {
        /*
         * Calculate Hijri Date only for a NEW document.
         *
         * Existing saved documents must not be modified
         * merely because they were opened.
         */
        if (
            frm.is_new() &&
            frm.doc.posting_date &&
            !frm.doc.custom_hijri_date
        ) {
            set_hijri_date(frm);
        }
    },

    refresh(frm) {
        frm.donor_companies = frm.donor_companies || [];

        setup_donation_filters(frm);

        if (frm.doc.donor) {
            load_donor_companies(frm, false);
        }

        if (frm.doc.company) {
            fetch_company_currency(frm, false);
        }

        /*
         * IMPORTANT:
         * Do NOT call set_hijri_date(frm) here.
         *
         * Doing that can modify the document every time it
         * is opened and cause ERPNext to show "Not Saved".
         */

        if (
            !frm.is_new() &&
            [1, 2].includes(frm.doc.docstatus)
        ) {
            add_accounting_ledger_button(frm);
        }
    },

    donor(frm) {
        frm.set_value('company', null);
        frm.set_value('donor_account', null);
        frm.set_value('cost_center', null);
        frm.set_value('project', null);
        frm.set_value('received_in_account', null);

        frm.donor_companies = [];

        if (!frm.doc.donor) {
            setup_donation_filters(frm);
            return;
        }

        load_donor_companies(frm, true);
    },

    company(frm) {
        frm.set_value('donor_account', null);
        frm.set_value('cost_center', null);
        frm.set_value('project', null);
        frm.set_value('received_in_account', null);

        frm.set_value('company_currency', null);
        frm.set_value('exchange_rate', null);
        frm.set_value('base_donation_amount', null);

        setup_donation_filters(frm);

        if (!frm.doc.company) {
            return;
        }

        if (frm.doc.donor) {
            fetch_donor_account(frm);
        }

        fetch_company_currency(frm, true);
    },

    posting_date(frm) {
        /*
         * Recalculate Hijri Date only when Posting Date
         * actually changes.
         */
        set_hijri_date(frm);

        if (
            frm.doc.company &&
            frm.doc.currency &&
            frm.doc.company_currency
        ) {
            fetch_company_exchange_rate(frm);
        }
    },

    currency(frm) {
        frm.set_value('exchange_rate', null);
        frm.set_value('base_donation_amount', null);

        if (
            frm.doc.company &&
            frm.doc.currency &&
            frm.doc.company_currency
        ) {
            fetch_company_exchange_rate(frm);
        }
    },

    donation_amount(frm) {
        calculate_base_amount(frm);
    },

    exchange_rate(frm) {
        calculate_base_amount(frm);
    },

    before_submit(frm) {
        if (!frm.doc.company) {
            frappe.throw(
                __('Company is required before submitting the Donation Entry.')
            );
        }

        if (!frm.doc.donor) {
            frappe.throw(
                __('Donor is required before submitting the Donation Entry.')
            );
        }

        if (!frm.doc.mode_of_payment) {
            frappe.throw(
                __('Mode of Payment is required before submitting the Donation Entry.')
            );
        }

        if (!frm.doc.received_in_account) {
            frappe.throw(
                __('Received In Account is required before submitting the Donation Entry.')
            );
        }

        if (!frm.doc.donor_account) {
            frappe.throw(
                __('Donor Account is required before submitting the Donation Entry.')
            );
        }

        /*
         * Cost Center may be empty while Draft,
         * but is mandatory on Submit.
         */
        if (!frm.doc.cost_center) {
            frappe.throw(
                __('Cost Center is mandatory before submitting the Donation Entry.')
            );
        }

        if (!frm.doc.currency) {
            frappe.throw(
                __('Currency is required before submitting the Donation Entry.')
            );
        }

        if (!frm.doc.company_currency) {
            frappe.throw(
                __('Company Currency is required before submitting the Donation Entry.')
            );
        }

        if (
            !flt(frm.doc.donation_amount) ||
            flt(frm.doc.donation_amount) <= 0
        ) {
            frappe.throw(
                __('Donation Amount must be greater than zero.')
            );
        }

        if (
            !flt(frm.doc.exchange_rate) ||
            flt(frm.doc.exchange_rate) <= 0
        ) {
            frappe.throw(
                __('A valid Company Exchange Rate is required before submitting.')
            );
        }

        if (
            !flt(frm.doc.base_donation_amount) ||
            flt(frm.doc.base_donation_amount) <= 0
        ) {
            frappe.throw(
                __('Base Donation Amount must be greater than zero.')
            );
        }

        /*
         * Fallback:
         * If Hijri Date is somehow empty, calculate it
         * immediately before Submit.
         */
        if (
            !frm.doc.custom_hijri_date &&
            frm.doc.posting_date
        ) {
            set_hijri_date(frm);
        }

        if (!frm.doc.custom_hijri_date) {
            frappe.throw(
                __(
                    'Hijri Date could not be calculated. Please change the Posting Date and try again.'
                )
            );
        }
    }
});


/* =========================================================
   HIJRI DATE
========================================================= */

/*
 * Uses the browser's Umm Al-Qura calendar.
 *
 * Stored value:
 * YYYY/M/D
 *
 * Example:
 * 1448/3/13
 *
 * IMPORTANT:
 * custom_hijri_date must be a DATA field,
 * NOT a Date field.
 */

function set_hijri_date(frm) {
    if (!frm.doc.posting_date) {
        if (frm.doc.custom_hijri_date) {
            frm.set_value(
                'custom_hijri_date',
                ''
            );
        }

        return;
    }

    try {
        const parts =
            frm.doc.posting_date.split('-');

        if (parts.length !== 3) {
            console.error(
                'Invalid Posting Date:',
                frm.doc.posting_date
            );

            return;
        }

        const year =
            parseInt(parts[0], 10);

        const month =
            parseInt(parts[1], 10) - 1;

        const day =
            parseInt(parts[2], 10);

        if (
            !year ||
            month < 0 ||
            month > 11 ||
            !day
        ) {
            console.error(
                'Invalid Posting Date values:',
                frm.doc.posting_date
            );

            return;
        }

        /*
         * Noon is deliberately used so browser timezone
         * handling does not move the date to the previous
         * or following Gregorian day.
         */
        const date = new Date(
            year,
            month,
            day,
            12,
            0,
            0
        );

        const formatter =
            new Intl.DateTimeFormat(
                'en-US-u-ca-islamic-umalqura',
                {
                    year: 'numeric',
                    month: 'numeric',
                    day: 'numeric'
                }
            );

        /*
         * Typical en-US output:
         *
         * 3/13/1448 AH
         *
         * meaning:
         * Month / Day / Year
         */
        const formatted =
            formatter.format(date);

        const clean =
            formatted
                .replace(/AH/gi, '')
                .trim();

        const hijri_parts =
            clean.split('/');

        if (hijri_parts.length !== 3) {
            console.error(
                'Unexpected Hijri Date format:',
                formatted
            );

            return;
        }

        const hijri_month =
            parseInt(
                hijri_parts[0],
                10
            );

        const hijri_day =
            parseInt(
                hijri_parts[1],
                10
            );

        const hijri_year =
            parseInt(
                hijri_parts[2],
                10
            );

        if (
            !hijri_year ||
            !hijri_month ||
            !hijri_day
        ) {
            console.error(
                'Could not parse Hijri Date:',
                formatted
            );

            return;
        }

        /*
         * Store consistently as:
         *
         * YYYY/M/D
         *
         * Example:
         * 1448/3/13
         */
        const hijri_date =
            hijri_year
            + '/'
            + hijri_month
            + '/'
            + hijri_day;

        /*
         * Only call set_value if the value really changed.
         *
         * This prevents unnecessary dirty-state changes.
         */
        if (
            frm.doc.custom_hijri_date !==
            hijri_date
        ) {
            frm.set_value(
                'custom_hijri_date',
                hijri_date
            );
        }

    } catch (error) {
        console.error(
            'Hijri Date conversion failed:',
            error
        );
    }
}


/* =========================================================
   DONOR COMPANIES
========================================================= */

function load_donor_companies(
    frm,
    auto_select = true
) {
    if (!frm.doc.donor) {
        return;
    }

    frappe.db.get_doc(
        'Donor',
        frm.doc.donor
    ).then(donor => {

        const rows =
            donor.custom_accounts || [];

        frm.donor_companies = rows
            .map(row => row.company)
            .filter(Boolean);

        frm.donor_companies = [
            ...new Set(frm.donor_companies)
        ];

        setup_donation_filters(frm);

        if (!frm.donor_companies.length) {
            frappe.msgprint({
                title: __('No Company'),
                indicator: 'orange',
                message: __(
                    'This donor does not have any Company configured in Accounts.'
                )
            });

            return;
        }

        /*
         * Auto-select Company when the Donor belongs
         * to only one Company.
         */
        if (
            auto_select &&
            frm.donor_companies.length === 1
        ) {
            frm.set_value(
                'company',
                frm.donor_companies[0]
            );
        }

        /*
         * Validate selected Company against Donor Accounts.
         */
        if (
            frm.doc.company &&
            !frm.donor_companies.includes(
                frm.doc.company
            )
        ) {
            frm.set_value(
                'company',
                null
            );

            frm.set_value(
                'donor_account',
                null
            );
        }
    });
}


/* =========================================================
   DONOR ACCOUNT
========================================================= */

function fetch_donor_account(frm) {
    if (
        !frm.doc.donor ||
        !frm.doc.company
    ) {
        return;
    }

    frappe.db.get_doc(
        'Donor',
        frm.doc.donor
    ).then(donor => {

        const rows =
            donor.custom_accounts || [];

        const match = rows.find(
            row =>
                row.company === frm.doc.company
        );

        if (
            match &&
            match.account
        ) {
            frm.set_value(
                'donor_account',
                match.account
            );

        } else {
            frm.set_value(
                'donor_account',
                null
            );

            frappe.msgprint({
                title:
                    __('Donor Account Missing'),

                indicator:
                    'orange',

                message: __(
                    'No Default Account is configured for this donor under company {0}.',
                    [frm.doc.company]
                )
            });
        }
    });
}


/* =========================================================
   FIELD FILTERS
========================================================= */

function setup_donation_filters(frm) {

    /* -------------------------------------------------------
       COMPANY
       Only Companies configured on the Donor
    ------------------------------------------------------- */

    frm.set_query(
        'company',
        function() {

            if (
                !frm.doc.donor ||
                !frm.donor_companies ||
                !frm.donor_companies.length
            ) {
                return {
                    filters: {
                        name: ['=', '']
                    }
                };
            }

            return {
                filters: {
                    name: [
                        'in',
                        frm.donor_companies
                    ]
                }
            };
        }
    );


    /* -------------------------------------------------------
       COST CENTER
    ------------------------------------------------------- */

    frm.set_query(
        'cost_center',
        function() {

            if (!frm.doc.company) {
                return {
                    filters: {
                        name: ['=', '']
                    }
                };
            }

            return {
                filters: {
                    company:
                        frm.doc.company,

                    is_group:
                        0
                }
            };
        }
    );


    /* -------------------------------------------------------
       PROJECT
    ------------------------------------------------------- */

    frm.set_query(
        'project',
        function() {

            if (!frm.doc.company) {
                return {
                    filters: {
                        name: ['=', '']
                    }
                };
            }

            return {
                filters: {
                    company:
                        frm.doc.company
                }
            };
        }
    );


    /* -------------------------------------------------------
       RECEIVED IN ACCOUNT
    ------------------------------------------------------- */

    frm.set_query(
        'received_in_account',
        function() {

            if (!frm.doc.company) {
                return {
                    filters: {
                        name: ['=', '']
                    }
                };
            }

            return {
                filters: {
                    company:
                        frm.doc.company,

                    is_group:
                        0,

                    disabled:
                        0
                }
            };
        }
    );


    /* -------------------------------------------------------
       DONOR ACCOUNT
    ------------------------------------------------------- */

    frm.set_query(
        'donor_account',
        function() {

            if (!frm.doc.company) {
                return {
                    filters: {
                        name: ['=', '']
                    }
                };
            }

            return {
                filters: {
                    company:
                        frm.doc.company,

                    is_group:
                        0,

                    disabled:
                        0
                }
            };
        }
    );
}


/* =========================================================
   COMPANY CURRENCY
========================================================= */

function fetch_company_currency(
    frm,
    fetch_rate = true
) {
    if (!frm.doc.company) {
        return;
    }

    frappe.db.get_value(
        'Company',
        frm.doc.company,
        'default_currency'
    ).then(r => {

        if (
            !r.message ||
            !r.message.default_currency
        ) {
            return;
        }

        const company_currency =
            r.message.default_currency;

        /*
         * Avoid unnecessary set_value calls.
         */
        if (
            frm.doc.company_currency !==
            company_currency
        ) {
            frm.set_value(
                'company_currency',
                company_currency
            );
        }

        if (!frm.doc.currency) {
            frm.set_value(
                'currency',
                company_currency
            );
        }

        if (fetch_rate) {
            fetch_company_exchange_rate(
                frm
            );
        }
    });
}


/* =========================================================
   COMPANY EXCHANGE RATE

   Uses Server Script API:
   get_company_exchange_rate
========================================================= */

function fetch_company_exchange_rate(frm) {
    if (
        !frm.doc.company ||
        !frm.doc.currency ||
        !frm.doc.company_currency
    ) {
        return;
    }

    const posting_date =
        frm.doc.posting_date ||
        frappe.datetime.get_today();

    frappe.call({
        method:
            'accounting_custom.api.exchange_rate.get_company_exchange_rate',

        args: {
            company:
                frm.doc.company,

            from_currency:
                frm.doc.currency,

            to_currency:
                frm.doc.company_currency,

            transaction_date:
                posting_date
        },

        freeze:
            false,

        callback(r) {

            if (
                !r.message ||
                !r.message.exchange_rate
            ) {
                frm.set_value(
                    'exchange_rate',
                    null
                );

                frm.set_value(
                    'base_donation_amount',
                    null
                );

                return;
            }

            const rate =
                flt(
                    r.message.exchange_rate
                );

            /*
             * Avoid unnecessary set_value.
             */
            if (
                flt(frm.doc.exchange_rate) !==
                rate
            ) {
                frm.set_value(
                    'exchange_rate',
                    rate
                );
            }

            calculate_base_amount(
                frm
            );
        }
    });
}


/* =========================================================
   BASE DONATION AMOUNT
========================================================= */

function calculate_base_amount(frm) {
    const amount =
        flt(
            frm.doc.donation_amount || 0
        );

    const rate =
        flt(
            frm.doc.exchange_rate || 0
        );

    const base_amount =
        amount && rate
            ? amount * rate
            : 0;

    /*
     * Avoid setting the same value repeatedly.
     */
    if (
        flt(frm.doc.base_donation_amount) !==
        flt(base_amount)
    ) {
        frm.set_value(
            'base_donation_amount',
            base_amount
        );
    }
}


/* =========================================================
   VIEW -> ACCOUNTING LEDGER
========================================================= */

function add_accounting_ledger_button(frm) {

    frm.add_custom_button(
        __('Accounting Ledger'),

        function() {

            frappe.route_options = null;

            const filters = {
                company:
                    frm.doc.company,

                from_date:
                    frm.doc.posting_date,

                to_date:
                    frm.doc.posting_date,

                voucher_no:
                    frm.doc.name,

                group_by:
                    ''
            };

            /*
             * Cancelled Donation Entries:
             * show cancelled accounting rows as well.
             */
            filters.show_cancelled_entries =
                frm.doc.docstatus === 2
                    ? 1
                    : 0;

            frappe.set_route(
                'query-report',
                'General Ledger',
                filters
            );
        },

        __('View')
    );
}
