#!/bin/bash

qpdf --empty \
  --pages \
  medical_dx_architecture_policy_proposal_v2.pdf \
  signature_pdf.pdf \
  -- \
  medical_dx_architecture_policy_proposal_attached.pdf
