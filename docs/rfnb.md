Our Python code generates Swiss Payment Code (SPC) QR bills. Currently the invoice number is written to the Ustrd (unstructured message) field, but it needs to be in the RfNb (reference number) field instead, so that an external portal reads it correctly.
Please:

Find the SPC generation code in this project
Add a function generate_scor(invoice_number: str) -> str that converts an arbitrary invoice number into a valid ISO 11649 Structured Creditor Reference (RF-reference), handling the MOD-97 checksum correctly
Change the SPC output so that:

RfTyp is set to "SCOR"
RfNb contains the generated SCOR reference
Ustrd is left empty


Add a unit test for generate_scor with at least 2 example invoice numbers, verifying the RF checksum is valid
