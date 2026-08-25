---
name: test-driven-development
description: Use when implementing any feature or bugfix, before writing implementation code
---

# Test-Driven Development (TDD)

## The Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Write the test first. Watch it fail. Write minimal code to pass. If you wrote code before the test, delete it and start over. Do not keep it as a reference. Do not adapt it. Do not look at it. Violating the letter of this rule is violating its spirit.

**When to use:** always — new features, bug fixes, refactoring, behavior changes.

**Exceptions** (require your human partner's approval): throwaway prototypes, generated code, configuration files.

## The Cycle: Red-Green-Refactor

### RED — Write the Failing Test

One minimal test that shows the expected behavior:

- One behavior per test
- The name describes the behavior
- Use real code. Mock only when unavoidable

<Good>
```typescript
test('retries failed operations 3 times', async () => {
  let attempts = 0;
  const operation = () => {
    attempts++;
    if (attempts < 3) throw new Error('fail');
    return 'success';
  };

  const result = await retryOperation(operation);

  expect(result).toBe('success');
  expect(attempts).toBe(3);
});
```
Clear name, tests real behavior, one thing
</Good>

<Bad>
```typescript
test('retry works', async () => {
  const mock = jest.fn()
    .mockRejectedValueOnce(new Error())
    .mockRejectedValueOnce(new Error())
    .mockResolvedValueOnce('success');
  await retryOperation(mock);
  expect(mock).toHaveBeenCalledTimes(3);
});
```
Vague name, tests mock not code
</Bad>

### Check RED — Watch It Fail (Mandatory)

```bash
npm test path/to/test.test.ts
```

Check:

- The test fails (does not error)
- The failure message is the expected one
- It fails because the behavior is missing, not because of typos

**Test passes immediately?** You are testing existing behavior. Fix the test.

**Test errors?** Fix the error. Re-run until it fails correctly.

### GREEN — Minimal Code

Write the simplest code that passes the test. Do not add extra features, options that nobody asked for, refactoring of other code, or "improvements" beyond the test.

### Check GREEN — Watch It Pass (Mandatory)

```bash
npm test path/to/test.test.ts
```

Check:

- The test passes
- Other tests still pass
- The output is pristine (no errors, no warnings)

**Test fails?** Fix the code, not the test.

**Other tests fail?** Fix them.

### REFACTOR — Clean Up

Only after green:

- Remove duplication
- Improve names
- Extract helpers

Keep tests green. Do not add behavior. Then repeat the cycle for the next behavior.

## Verification Checklist

Before marking work complete:

- [ ] Every new function/method has a test
- [ ] You watched each test fail before implementing
- [ ] Each test failed for the expected reason (missing behavior, not typos)
- [ ] You wrote minimal code to pass each test
- [ ] All tests pass and the output is pristine (no errors, no warnings)
- [ ] Tests use real code (mocks only if unavoidable)
- [ ] Test docstrings say what behavior the test proves and why, per writing-developer-facing-text (pragmatic mode)
- [ ] Edge cases and error paths that the requirement names are covered

If any box is unchecked, you skipped TDD. Start over.

## When Stuck

| Problem | Action |
|---------|--------|
| You do not know how to test | Write the wished-for API. Write the assertion first. Ask your human partner. |
| The test is too complicated | The design is too complicated. Simplify the interface. |
| You must mock everything | The code is too coupled. Use dependency injection. |
| The test setup is huge | Extract helpers. If the design is still complex, simplify it. |

## Debugging Integration

If you find a bug, write a failing test that reproduces it. Then follow the cycle. The test proves the fix and prevents regression. Never fix a bug without a test.

## Testing Anti-Patterns

When adding mocks or test utilities, read `testing-anti-patterns.md` (in this directory) first:

- Testing mock behavior instead of real behavior
- Adding test-only methods to production classes
- Mocking without understanding dependencies
