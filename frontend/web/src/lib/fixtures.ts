/**
 * Fixtures used only when the backend endpoint does not exist yet.
 *
 * Shapes are copied from Phụ lục B of the spec so the layout that renders here is
 * the layout the real payload will get. Anything served from this file is tagged
 * `source: 'MOCK'` by the API client and must show the mock badge — the spec
 * forbids silent fallback (§4.2 "Silent fallback", §11.2 T11).
 */
import type {
  AuditEvent,
  ChangeEventSummary,
  ComplianceCheckStatusResponse,
  ComplianceReviewReport,
  DocumentSummary,
  EvidenceQueryResponse,
  HealthDetailsResponse,
  OverviewStats,
  PolicyLinkSummary,
  RegulatoryImpactReport,
  RegulatorySourceStatusResponse,
  ReviewTaskSummary,
  SourceReviewPackage,
} from '@/types/api'

export const MOCK_SOURCE_ID = 'doc-001'
export const MOCK_CHECK_ID = 'check-001'
export const MOCK_IMPACT_ID = 'impact-001'

export function mockOverview(): OverviewStats {
  return {
    authority_sources_active: 4,
    sources_pending_review: 2,
    change_events_recent: 3,
    policy_links_pending: 5,
    compliance_checks_open: 1,
    claims_needing_action: 4,
  }
}

export function mockDocuments(): DocumentSummary[] {
  return [
    {
      document_id: MOCK_SOURCE_ID,
      filename: '06-2025-TT-NHNN.pdf',
      document_number: '06/2025/TT-NHNN',
      title: 'Thông tư sửa đổi Thông tư 07/2024/TT-NHNN',
      issuer: 'Ngân hàng Nhà nước Việt Nam',
      document_class: 'EXTERNAL_LEGAL',
      subtype: 'AMENDMENT',
      upload_purpose: 'ADD_REGULATORY_SOURCE',
      trust_class: 'AUTHORITY_SOURCE_CANDIDATE',
      status: 'REVIEW_REQUIRED',
      issued_date: '2025-05-20',
      effective_date: '2025-07-01',
      uploaded_at: '2026-07-18T08:12:00Z',
    },
    {
      document_id: 'doc-002',
      filename: '07-2024-TT-NHNN.pdf',
      document_number: '07/2024/TT-NHNN',
      title: 'Thông tư quy định về hoạt động cấp tín dụng',
      issuer: 'Ngân hàng Nhà nước Việt Nam',
      document_class: 'EXTERNAL_LEGAL',
      subtype: 'CIRCULAR',
      upload_purpose: 'ADD_REGULATORY_SOURCE',
      trust_class: 'AUTHORITY_SOURCE',
      status: 'ACTIVE',
      issued_date: '2024-03-15',
      effective_date: '2024-05-01',
      valid_from: '2024-05-01',
    },
    {
      document_id: 'policy-001',
      filename: 'quy-trinh-cap-tin-dung-sme.pdf',
      document_number: 'NB-SME-01',
      title: 'Quy trình cấp tín dụng SME nội bộ',
      issuer: 'Khối Khách hàng Doanh nghiệp',
      document_class: 'INTERNAL_POLICY',
      subtype: 'INTERNAL_POLICY',
      // No upload_purpose: an INTERNAL_APPROVED policy does not arrive through
      // either of the two upload flows. §2.4 says promoting a document into
      // internal-approved requires its own workflow, so claiming
      // ADD_REGULATORY_SOURCE here would contradict §7.2 (that purpose always
      // starts at AUTHORITY_SOURCE_CANDIDATE).
      upload_purpose: null,
      trust_class: 'INTERNAL_APPROVED',
      status: 'ACTIVE',
      effective_date: '2025-02-05',
    },
    {
      document_id: 'review-doc-001',
      filename: 'bao-cao-tuan-thu-q2.pdf',
      title: 'Báo cáo tuân thủ quý 2/2026',
      document_class: 'REVIEW_DOCUMENT',
      upload_purpose: 'CHECK_DOCUMENT_COMPLIANCE',
      trust_class: 'REVIEW_TARGET',
      status: 'REVIEW_REQUIRED',
      check_id: MOCK_CHECK_ID,
      uploaded_at: '2026-07-18T09:40:00Z',
    },
  ]
}

export function mockSourceStatus(documentId: string): RegulatorySourceStatusResponse {
  const doc = mockDocuments().find((d) => d.document_id === documentId) ?? mockDocuments()[0]
  return {
    document_id: documentId,
    status: 'REVIEW_REQUIRED',
    trust_class: 'AUTHORITY_SOURCE_CANDIDATE',
    completed_steps: ['RECEIVED', 'QUARANTINED', 'EXTRACTED', 'PARSED'],
    document: doc,
  }
}

/** Phụ lục B.1 — Regulatory Source Review Package. */
export function mockReviewPackage(documentId: string): SourceReviewPackage {
  return {
    document_id: documentId,
    trust_class: 'AUTHORITY_SOURCE_CANDIDATE',
    status: 'REVIEW_REQUIRED',
    metadata: {
      document_number: {
        value: '06/2025/TT-NHNN',
        page: 1,
        evidence_text: 'Thông tư số 06/2025/TT-NHNN ngày 20 tháng 5 năm 2025',
        confidence: 0.98,
      },
      title: {
        value: 'Thông tư sửa đổi, bổ sung một số điều của Thông tư 07/2024/TT-NHNN',
        page: 1,
        evidence_text: 'Sửa đổi, bổ sung một số điều của Thông tư số 07/2024/TT-NHNN',
        confidence: 0.95,
      },
      issuer: {
        value: 'Ngân hàng Nhà nước Việt Nam',
        page: 1,
        evidence_text: 'NGÂN HÀNG NHÀ NƯỚC VIỆT NAM',
        confidence: 0.99,
      },
      issued_date: { value: '2025-05-20', page: 1, evidence_text: 'ngày 20 tháng 5 năm 2025', confidence: 0.97 },
      effective_date: {
        value: '2025-07-01',
        page: 3,
        evidence_text: 'Thông tư này có hiệu lực thi hành kể từ ngày 01 tháng 7 năm 2025',
        confidence: 0.94,
      },
    },
    provisions: [
      {
        provision_id: 'prov-a1',
        locator: 'Điều 1',
        heading: 'Phạm vi điều chỉnh',
        content: 'Thông tư này sửa đổi, bổ sung một số điều của Thông tư 07/2024/TT-NHNN.',
        page: 1,
        evidence_span_id: null,
      },
      {
        provision_id: 'prov-a2',
        locator: 'Điều 2',
        heading: 'Nội dung sửa đổi',
        content: 'Sửa đổi khoản 7 Điều 7; thay cụm từ tại khoản 3 Điều 12; bãi bỏ khoản 2 Điều 15.',
        page: 2,
        evidence_span_id: 'ev-001',
      },
      {
        provision_id: 'prov-a3',
        locator: 'Điều 3',
        heading: 'Hiệu lực thi hành',
        content: 'Thông tư này có hiệu lực thi hành kể từ ngày 01 tháng 7 năm 2025.',
        page: 3,
        evidence_span_id: null,
      },
    ],
    references: [
      {
        reference_id: 'ref-001',
        raw_text: 'Thông tư số 07/2024/TT-NHNN',
        target_document_number: '07/2024/TT-NHNN',
        target_locator: null,
        resolution_status: 'EXACT',
        evidence_span_id: 'ev-001',
      },
      {
        reference_id: 'ref-002',
        raw_text: 'quy định của pháp luật về phòng, chống rửa tiền',
        target_document_number: null,
        target_locator: null,
        resolution_status: 'UNRESOLVED',
        evidence_span_id: null,
      },
    ],
    change_proposals: [
      {
        proposal_id: 'prop-001',
        review_task_id: 'rev-001',
        operation: 'REPLACE_PROVISION',
        target: { document_number: '07/2024/TT-NHNN', article: '7', clause: '7' },
        resolution_status: 'EXACT',
        before_text: 'Hạn mức cấp tín dụng đối với khách hàng SME tối đa là 500 triệu đồng.',
        after_text: 'Hạn mức cấp tín dụng đối với khách hàng SME tối đa là 700 triệu đồng.',
        effective_date: '2025-07-01',
        evidence_span_id: 'ev-001',
        review_status: 'PENDING',
        is_critical: true,
        confidence: 0.96,
        warnings: [],
      },
      {
        proposal_id: 'prop-002',
        review_task_id: 'rev-002',
        operation: 'REPLACE_TEXT',
        target: { document_number: '07/2024/TT-NHNN', article: '12', clause: '3' },
        resolution_status: 'AMBIGUOUS',
        before_text: 'bộ phận quản lý rủi ro',
        after_text: 'bộ phận quản lý rủi ro độc lập',
        effective_date: '2025-07-01',
        evidence_span_id: 'ev-002',
        review_status: 'PENDING',
        is_critical: true,
        confidence: 0.71,
        warnings: ['Cụm từ xuất hiện ở 2 vị trí — target mơ hồ, cần người xác nhận.'],
      },
      {
        proposal_id: 'prop-003',
        review_task_id: 'rev-004',
        operation: 'REPEAL_PROVISION',
        target: { document_number: '07/2024/TT-NHNN', article: '15', clause: '2' },
        resolution_status: 'EXACT',
        before_text: 'Khoản 2 Điều 15 quy định về báo cáo định kỳ hằng tháng.',
        after_text: null,
        effective_date: '2025-07-01',
        evidence_span_id: 'ev-003',
        review_status: 'APPROVED',
        is_critical: false,
        confidence: 0.9,
        warnings: [],
      },
    ],
    evidence_spans: [
      {
        evidence_span_id: 'ev-001',
        document_id: documentId,
        page: 2,
        text: 'Sửa đổi khoản 7 Điều 7 như sau: “Hạn mức cấp tín dụng đối với khách hàng SME tối đa là 700 triệu đồng.”',
        bbox: [72, 210, 523, 268],
        extractor: 'rule_parser',
        confidence: 0.96,
      },
      {
        evidence_span_id: 'ev-002',
        document_id: documentId,
        page: 2,
        text: 'Thay cụm từ “bộ phận quản lý rủi ro” bằng cụm từ “bộ phận quản lý rủi ro độc lập”.',
        bbox: [72, 300, 523, 342],
        extractor: 'llm_extraction',
        confidence: 0.71,
      },
      {
        evidence_span_id: 'ev-003',
        document_id: documentId,
        page: 3,
        text: 'Bãi bỏ khoản 2 Điều 15.',
        bbox: [72, 120, 400, 150],
        extractor: 'rule_parser',
        confidence: 0.9,
      },
    ],
    warnings: [
      'OCR confidence trang 2 thấp (0.71) — cần đối chiếu bản gốc.',
      'Có 1 dẫn chiếu chưa resolve tới văn bản ngoài kho.',
    ],
    pending_critical_reviews: 2,
  }
}

export function mockChangeEvents(): ChangeEventSummary[] {
  return [
    {
      change_event_id: 'chg-001',
      operation: 'REPLACE_PROVISION',
      provision_locator: 'Điều 7 › Khoản 7',
      target_document_number: '07/2024/TT-NHNN',
      source_document_number: '06/2025/TT-NHNN',
      before_version_id: 'ver-d7k2-v1',
      after_version_id: 'ver-d7k2-v2',
      effective_date: '2025-07-01',
      status: 'APPLIED',
      evidence_span_id: 'ev-001',
      before_text: 'Hạn mức cấp tín dụng đối với khách hàng SME tối đa là 500 triệu đồng.',
      after_text: 'Hạn mức cấp tín dụng đối với khách hàng SME tối đa là 700 triệu đồng.',
    },
    {
      change_event_id: 'chg-002',
      operation: 'REPEAL_PROVISION',
      provision_locator: 'Điều 15 › Khoản 2',
      target_document_number: '07/2024/TT-NHNN',
      source_document_number: '06/2025/TT-NHNN',
      before_version_id: 'ver-d15k2-v1',
      after_version_id: null,
      effective_date: '2025-07-01',
      status: 'APPLIED',
      evidence_span_id: 'ev-003',
      before_text: 'Khoản 2 Điều 15 quy định về báo cáo định kỳ hằng tháng.',
      after_text: null,
    },
    {
      change_event_id: 'chg-003',
      operation: 'REPLACE_TEXT',
      provision_locator: 'Điều 12 › Khoản 3',
      target_document_number: '07/2024/TT-NHNN',
      source_document_number: '06/2025/TT-NHNN',
      before_version_id: 'ver-d12k3-v1',
      after_version_id: null,
      effective_date: '2025-07-01',
      status: 'PENDING_REVIEW',
      evidence_span_id: 'ev-002',
      before_text: 'Hồ sơ tín dụng SME phải được thẩm định bởi bộ phận quản lý rủi ro.',
      after_text: 'Hồ sơ tín dụng SME phải được thẩm định bởi bộ phận quản lý rủi ro độc lập.',
    },
  ]
}

export function mockPolicyLinks(): PolicyLinkSummary[] {
  return [
    {
      policy_link_id: 'link-001',
      policy_clause_id: 'pc-001',
      policy_document_title: 'Quy trình cấp tín dụng SME nội bộ',
      policy_locator: 'Mục 3.2',
      provision_id: 'prov-d7k7',
      provision_locator: '07/2024/TT-NHNN › Điều 7 › Khoản 7',
      relation: 'IMPLEMENTS',
      confidence: 0.93,
      review_status: 'PENDING',
      owner: 'Khối KHDN',
    },
    {
      policy_link_id: 'link-002',
      policy_clause_id: 'pc-004',
      policy_document_title: 'Quy trình cấp tín dụng SME nội bộ',
      policy_locator: 'Mục 5.1',
      provision_id: 'prov-d12k3',
      provision_locator: '07/2024/TT-NHNN › Điều 12 › Khoản 3',
      relation: 'REFERENCES',
      confidence: 0.68,
      review_status: 'PENDING',
      owner: 'Khối QLRR',
    },
    {
      policy_link_id: 'link-003',
      policy_clause_id: 'pc-007',
      policy_document_title: 'Chính sách báo cáo nội bộ',
      policy_locator: 'Mục 2.4',
      provision_id: 'prov-d15k2',
      provision_locator: '07/2024/TT-NHNN › Điều 15 › Khoản 2',
      relation: 'IMPLEMENTS',
      confidence: 0.88,
      review_status: 'APPROVED',
      owner: 'Ban Pháp chế',
    },
  ]
}

export function mockImpactReports(): RegulatoryImpactReport[] {
  return [mockImpactReport(MOCK_SOURCE_ID)]
}

export function mockImpactReport(sourceDocumentId: string): RegulatoryImpactReport {
  return {
    report_id: MOCK_IMPACT_ID,
    source_document_id: sourceDocumentId,
    source_document_number: '06/2025/TT-NHNN',
    generated_at: '2026-07-18T10:05:00Z',
    change_event_ids: ['chg-001', 'chg-002'],
    change_events: mockChangeEvents().slice(0, 2),
    impacted_policy_clauses: [
      {
        policy_clause_id: 'pc-001',
        policy_document_title: 'Quy trình cấp tín dụng SME nội bộ',
        locator: 'Mục 3.2',
        content: 'Hạn mức cấp tín dụng SME tối đa là 500 triệu đồng, thời hạn tối đa 12 tháng.',
        severity: 'HIGH',
        owner: 'Khối KHDN',
        recommended_action: 'Cập nhật hạn mức 500 triệu → 700 triệu theo hiệu lực 01/07/2025.',
        evidence_span_ids: ['ev-001'],
      },
      {
        policy_clause_id: 'pc-007',
        policy_document_title: 'Chính sách báo cáo nội bộ',
        locator: 'Mục 2.4',
        content: 'Đơn vị thực hiện báo cáo định kỳ hằng tháng theo Khoản 2 Điều 15.',
        severity: 'MEDIUM',
        owner: 'Ban Pháp chế',
        recommended_action: 'Bỏ tham chiếu Khoản 2 Điều 15 (đã bị bãi bỏ).',
        evidence_span_ids: ['ev-003'],
      },
    ],
    summary:
      '2 ChangeEvent được áp dụng từ 01/07/2025, ảnh hưởng 2 điều khoản policy nội bộ (1 HIGH, 1 MEDIUM).',
    status: 'REVIEW_REQUIRED',
  }
}

export function mockCheckStatus(checkId: string): ComplianceCheckStatusResponse {
  return {
    check_id: checkId,
    target_document_id: 'review-doc-001',
    status: 'REVIEW_REQUIRED',
    completed_steps: ['RECEIVED', 'QUARANTINED', 'EXTRACTED', 'CLAIMS_PARSED', 'CHECKING'],
    document: mockDocuments()[3],
    review_date: '2026-07-18',
    requested_scope: ['Tín dụng SME'],
  }
}

/** Phụ lục B.2 + B.3 — Compliance Review Report with claim assessments. */
export function mockComplianceReport(checkId: string): ComplianceReviewReport {
  return {
    report_id: `report-${checkId}`,
    check_id: checkId,
    target_document_id: 'review-doc-001',
    target_document_title: 'Báo cáo tuân thủ quý 2/2026',
    review_date: '2026-07-18',
    requested_scope: ['Tín dụng SME'],
    summary: {
      total_claims: 12,
      compliant: 7,
      non_compliant: 2,
      partially_compliant: 0,
      outdated_reference: 1,
      missing_evidence: 1,
      ambiguous: 0,
      needs_human_review: 1,
    },
    assessments: [
      {
        claim_id: 'claim-001',
        review_task_id: 'rev-101',
        section: 'Mục 3.2',
        source_text: 'Hạn mức tối đa là 500 triệu đồng.',
        status: 'OUTDATED_REFERENCE',
        structured_facts: { threshold: 500000000, currency: 'VND' },
        valid_evidence: [
          {
            document_number: '07/2024/TT-NHNN',
            article: '7',
            clause: '7',
            version: 'V2',
            effective_from: '2025-07-01',
            page: 3,
            text: 'Hạn mức cấp tín dụng đối với khách hàng SME tối đa là 700 triệu đồng.',
            evidence_span_id: 'ev-001',
            trust_class: 'AUTHORITY_SOURCE',
          },
        ],
        excluded_evidence: [{ version: 'V1', reason: 'SUPERSEDED_AT_REVIEW_DATE', document_number: '07/2024/TT-NHNN' }],
        explanation: 'Tài liệu dùng hạn mức của phiên bản cũ.',
        recommendation: 'Cập nhật 500 triệu đồng thành 700 triệu đồng.',
        confidence: 0.96,
        severity: 'HIGH',
        review_status: 'PENDING',
      },
      {
        claim_id: 'claim-002',
        review_task_id: 'rev-102',
        section: 'Mục 4.1',
        source_text: 'Hồ sơ tín dụng SME được thẩm định bởi bộ phận quản lý rủi ro.',
        status: 'PARTIALLY_COMPLIANT',
        valid_evidence: [
          {
            document_number: '07/2024/TT-NHNN',
            article: '12',
            clause: '3',
            version: 'V2',
            effective_from: '2025-07-01',
            page: 5,
            text: 'Hồ sơ tín dụng SME phải được thẩm định bởi bộ phận quản lý rủi ro độc lập.',
            evidence_span_id: 'ev-002',
            trust_class: 'AUTHORITY_SOURCE',
          },
        ],
        excluded_evidence: [],
        explanation: 'Thiếu điều kiện "độc lập" so với quy định hiện hành.',
        recommendation: 'Bổ sung yêu cầu bộ phận quản lý rủi ro độc lập.',
        confidence: 0.84,
        severity: 'MEDIUM',
        review_status: 'PENDING',
      },
      {
        claim_id: 'claim-003',
        review_task_id: 'rev-103',
        section: 'Mục 2.4',
        source_text: 'Đơn vị nộp báo cáo định kỳ hằng tháng.',
        status: 'NON_COMPLIANT',
        valid_evidence: [
          {
            document_number: '06/2025/TT-NHNN',
            article: '2',
            version: 'V1',
            effective_from: '2025-07-01',
            page: 3,
            text: 'Bãi bỏ khoản 2 Điều 15 Thông tư 07/2024/TT-NHNN.',
            evidence_span_id: 'ev-003',
            trust_class: 'AUTHORITY_SOURCE',
          },
        ],
        excluded_evidence: [{ version: 'V1', reason: 'REPEALED', document_number: '07/2024/TT-NHNN' }],
        explanation: 'Nghĩa vụ báo cáo hằng tháng đã bị bãi bỏ từ 01/07/2025.',
        recommendation: 'Bỏ yêu cầu báo cáo định kỳ hằng tháng.',
        confidence: 0.91,
        severity: 'HIGH',
        review_status: 'PENDING',
      },
      {
        claim_id: 'claim-004',
        review_task_id: 'rev-104',
        section: 'Mục 6.3',
        source_text: 'Thời gian lưu trữ hồ sơ là 7 năm.',
        status: 'MISSING_EVIDENCE',
        valid_evidence: [],
        excluded_evidence: [],
        explanation: 'Không tìm thấy căn cứ đủ mạnh trong kho nguồn đã duyệt.',
        recommendation: null,
        confidence: 0.42,
        severity: 'LOW',
        review_status: 'PENDING',
      },
      {
        claim_id: 'claim-005',
        review_task_id: 'rev-105',
        section: 'Mục 1.1',
        source_text: 'Chính sách áp dụng cho toàn bộ khách hàng doanh nghiệp.',
        status: 'COMPLIANT',
        valid_evidence: [
          {
            document_number: '07/2024/TT-NHNN',
            article: '1',
            version: 'V2',
            effective_from: '2025-07-01',
            page: 1,
            text: 'Thông tư này áp dụng đối với tổ chức tín dụng và khách hàng doanh nghiệp.',
            trust_class: 'AUTHORITY_SOURCE',
          },
        ],
        excluded_evidence: [],
        explanation: 'Phạm vi áp dụng khớp với quy định hiện hành.',
        recommendation: null,
        confidence: 0.95,
        severity: 'LOW',
        review_status: 'APPROVED',
        reviewer_action: 'CONFIRM',
      },
      {
        claim_id: 'claim-006',
        review_task_id: 'rev-106',
        section: 'Mục 5.5',
        source_text: 'Lãi suất ưu đãi được áp dụng theo quyết định của Tổng Giám đốc.',
        status: 'NEEDS_HUMAN_REVIEW',
        valid_evidence: [],
        excluded_evidence: [],
        explanation: 'Rule và LLM không đồng thuận; confidence thấp.',
        recommendation: null,
        confidence: 0.38,
        severity: 'MEDIUM',
        review_status: 'PENDING',
      },
    ],
    actions: [
      {
        action_id: 'act-001',
        claim_id: 'claim-001',
        action: 'Cập nhật hạn mức SME 500 triệu → 700 triệu trong Quy trình cấp tín dụng.',
        owner: 'Khối KHDN',
        due_date: '2026-08-15',
        status: 'OPEN',
      },
      {
        action_id: 'act-002',
        claim_id: 'claim-003',
        action: 'Bỏ yêu cầu báo cáo định kỳ hằng tháng (Khoản 2 Điều 15 đã bãi bỏ).',
        owner: 'Ban Pháp chế',
        due_date: '2026-08-01',
        status: 'OPEN',
      },
    ],
    status: 'REVIEW_REQUIRED',
  }
}

export function mockReviewTasks(): ReviewTaskSummary[] {
  return [
    {
      task_id: 'rev-001',
      task_type: 'CHANGE_PROPOSAL',
      target_id: 'prop-001',
      target_label: 'REPLACE_PROVISION · 07/2024/TT-NHNN Điều 7 Khoản 7',
      document_id: MOCK_SOURCE_ID,
      risk: 'HIGH',
      status: 'PENDING',
      created_at: '2026-07-18T08:15:00Z',
      is_critical: true,
    },
    {
      task_id: 'rev-002',
      task_type: 'CHANGE_PROPOSAL',
      target_id: 'prop-002',
      target_label: 'REPLACE_TEXT · target mơ hồ',
      document_id: MOCK_SOURCE_ID,
      risk: 'HIGH',
      status: 'PENDING',
      created_at: '2026-07-18T08:15:00Z',
      is_critical: true,
    },
    {
      task_id: 'rev-003',
      task_type: 'POLICY_LINK',
      target_id: 'link-002',
      target_label: 'Quy trình SME Mục 5.1 ↔ Điều 12 Khoản 3',
      risk: 'MEDIUM',
      status: 'PENDING',
      created_at: '2026-07-18T10:06:00Z',
      is_critical: false,
    },
  ]
}

export function mockEvidenceQuery(question: string): EvidenceQueryResponse {
  return {
    question,
    query_date: '2026-07-18',
    answer:
      'Hạn mức cấp tín dụng SME tối đa là 700 triệu đồng, áp dụng từ 01/07/2025 theo Điều 7 Khoản 7 Thông tư 07/2024/TT-NHNN (bản V2 sau sửa đổi bởi 06/2025/TT-NHNN).',
    valid_evidence: [
      {
        document_number: '07/2024/TT-NHNN',
        article: '7',
        clause: '7',
        version: 'V2',
        effective_from: '2025-07-01',
        page: 3,
        text: 'Hạn mức cấp tín dụng đối với khách hàng SME tối đa là 700 triệu đồng.',
        evidence_span_id: 'ev-001',
        trust_class: 'AUTHORITY_SOURCE',
      },
    ],
    excluded_evidence: [
      { version: 'V1', document_number: '07/2024/TT-NHNN', reason: 'SUPERSEDED_AT_QUERY_DATE' },
      { document_number: '06/2025/TT-NHNN', reason: 'NOT_YET_ACTIVE' },
    ],
    change_history: mockChangeEvents().slice(0, 1),
    needs_human_review: false,
  }
}

export function mockAudit(): AuditEvent[] {
  return [
    {
      audit_id: 'aud-003',
      actor: 'officer',
      action: 'CHANGE_PROPOSAL_APPROVED',
      entity: 'ChangeProposal',
      entity_id: 'prop-003',
      before: { review_status: 'PENDING' },
      after: { review_status: 'APPROVED' },
      timestamp: '2026-07-18T09:02:11Z',
    },
    {
      audit_id: 'aud-002',
      actor: 'system',
      action: 'SOURCE_PARSED',
      entity: 'Document',
      entity_id: MOCK_SOURCE_ID,
      before: { status: 'EXTRACTED' },
      after: { status: 'PARSED' },
      timestamp: '2026-07-18T08:14:02Z',
    },
    {
      audit_id: 'aud-001',
      actor: 'officer',
      action: 'SOURCE_UPLOADED',
      entity: 'Document',
      entity_id: MOCK_SOURCE_ID,
      before: null,
      after: { trust_class: 'AUTHORITY_SOURCE_CANDIDATE' },
      timestamp: '2026-07-18T08:12:00Z',
    },
  ]
}

export function mockHealth(): HealthDetailsResponse {
  return {
    status: 'degraded',
    demo_mode: true,
    components: [
      { name: 'PostgreSQL', mode: 'REAL', healthy: true, detail: 'sqlite fallback engine' },
      { name: 'OpenSearch', mode: 'MOCK', healthy: false, detail: 'in-memory stub' },
      { name: 'Neo4j', mode: 'MOCK', healthy: false, detail: 'in-memory stub' },
      { name: 'LLM', mode: 'MOCK', healthy: false, detail: 'deterministic mock provider' },
      { name: 'Embedding', mode: 'MOCK', healthy: false, detail: 'hash embedding' },
    ],
  }
}
