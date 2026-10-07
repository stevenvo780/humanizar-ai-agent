import { describe, expect, it } from 'vitest';
import { actionProposal } from './actions';
import type { ToolTrace } from '../../shared/api/types';

function trace(output: unknown): ToolTrace {
  return {
    id: 'proposal',
    tool: 'create_demo_request',
    input: {},
    output: JSON.stringify(output),
    status: 'completed',
    duration_ms: 1,
  };
}
describe('explicit customer action proposals', () => {
  it('recognizes pending demo requests rather than treating the trace as an executed action', () => {
    expect(
      actionProposal(
        trace({
          requires_confirmation: true,
          action: { tool: 'create_demo_request', input: { interest: 'Cauce V3' } },
          message: 'Confirma tu demo',
        }),
      ),
    ).toEqual({
      tool: 'create_demo_request',
      input: { interest: 'Cauce V3' },
      message: 'Confirma tu demo',
    });
  });
  it('does not accept a terminal or arbitrary tool proposal', () => {
    expect(
      actionProposal(
        trace({
          requires_confirmation: true,
          action: { tool: 'terminal', input: { command: 'pwd' } },
        }),
      ),
    ).toBeNull();
  });
  it('requires explicit pending status and object input', () => {
    expect(
      actionProposal(trace({ action: { tool: 'create_demo_request', input: {} } })),
    ).toBeNull();
    expect(
      actionProposal(
        trace({ requires_confirmation: true, action: { tool: 'create_demo_request', input: [] } }),
      ),
    ).toBeNull();
  });
});
