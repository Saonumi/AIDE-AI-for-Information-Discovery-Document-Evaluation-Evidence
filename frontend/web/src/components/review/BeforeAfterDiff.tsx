/**
 * before_after_diff (spec §10.6, required by §3.1.1 and §10.3).
 *
 * Side-by-side current version vs proposed version.
 *
 * A repeal is identified by its OPERATION, never by a missing "after" text:
 * REPLACE_TEXT on a proposal that has not been applied yet also has no after
 * version, and rendering that as "đã bãi bỏ" would misinform the reviewer about
 * what the amendment does.
 */
import { AMENDMENT_OPERATION_LABEL } from '@/lib/labels'
import { AMENDMENT_OPERATION, type AmendmentOperation } from '@/types/domain'

export function BeforeAfterDiff({
  before,
  after,
  effectiveDate,
  operation,
}: {
  before?: string | null
  after?: string | null
  effectiveDate?: string | null
  operation?: AmendmentOperation | string
}) {
  const isRepeal = operation === AMENDMENT_OPERATION.REPEAL_PROVISION
  const hasAfter = after != null && after !== ''

  return (
    <div className="diff" data-testid="before-after-diff" data-operation={operation}>
      <div className="diff__col diff__col--before">
        <h5 className="diff__title">Hiện tại (before)</h5>
        <p className="diff__text">{before || <em>Không có nội dung trước đó</em>}</p>
      </div>

      <div className="diff__col diff__col--after">
        <h5 className="diff__title">Sau sửa đổi (after)</h5>
        {isRepeal ? (
          <p className="diff__text diff__text--repealed" data-testid="diff-repealed">
            Điều khoản bị bãi bỏ — version hiện tại được đóng hiệu lực, lịch sử vẫn giữ nguyên.
          </p>
        ) : hasAfter ? (
          <p className="diff__text">{after}</p>
        ) : (
          <p className="diff__text diff__text--pending" data-testid="diff-pending">
            {/* State a fact about the payload, not about the workflow: this
                component does not know whether the change was applied. */}
            <em>
              Không có nội dung sau sửa đổi trong dữ liệu
              {operation
                ? ` cho thao tác ${AMENDMENT_OPERATION_LABEL[operation as AmendmentOperation] ?? operation}`
                : ''}
              .
            </em>
          </p>
        )}
      </div>

      <div className="diff__meta">
        <span>
          Ngày hiệu lực: <strong data-testid="diff-effective-date">{effectiveDate ?? 'chưa xác định'}</strong>
        </span>
      </div>
    </div>
  )
}
