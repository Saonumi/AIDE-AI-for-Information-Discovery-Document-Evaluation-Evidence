/**
 * Pipeline stepper — §10.3 "Hiển thị pipeline state theo bước."
 *
 * Works for both state machines (§2.4) by taking the ordered step list and the
 * set of completed steps. Terminal failure states are not on the happy path, so
 * they surface as a separate note instead of a fake step.
 */
export function PipelineSteps({
  steps,
  completed,
  current,
  labels,
}: {
  steps: readonly string[]
  completed: readonly string[]
  current?: string
  labels: Record<string, string>
}) {
  const offPath = current && !steps.includes(current) ? current : null

  return (
    <div className="pipeline" data-testid="pipeline-steps">
      <ol className="pipeline__list">
        {steps.map((step) => {
          const isDone = completed.includes(step)
          const isCurrent = step === current
          return (
            <li
              key={step}
              className="pipeline__step"
              data-step={step}
              data-state={isCurrent ? 'current' : isDone ? 'done' : 'pending'}
            >
              <span className="pipeline__marker" aria-hidden />
              <span className="pipeline__label">{labels[step] ?? step}</span>
            </li>
          )
        })}
      </ol>
      {offPath && (
        <p className="pipeline__off-path" data-testid="pipeline-off-path" data-state={offPath}>
          Trạng thái hiện tại nằm ngoài luồng chuẩn: <strong>{labels[offPath] ?? offPath}</strong>
        </p>
      )}
    </div>
  )
}
