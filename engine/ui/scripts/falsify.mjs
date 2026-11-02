#!/usr/bin/env node
// Apply one registered falsifier (e2e/falsifiers.json), build, run its checks and require red; restore the
// source, run the same checks on the unchanged build and require green. Records both under
// proof/VELDO-0145/falsifiers/<case>.json. Source files are restored even when a check fails or throws.
import { spawnSync } from 'node:child_process'
import { cpSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { createHash } from 'node:crypto'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const UI = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const ROOT = path.resolve(UI, '..', '..')
const OUT = path.join(ROOT, 'proof', 'VELDO-0145', 'falsifiers')
const registry = JSON.parse(readFileSync(path.join(UI, 'e2e', 'falsifiers.json'), 'utf8')).cases
const sha = (text) => createHash('sha256').update(text).digest('hex')

function run(command, args, env = {}) {
  const started = Date.now()
  const done = spawnSync(command, args, { cwd: UI, env: { ...process.env, ...env }, encoding: 'utf8', maxBuffer: 64 << 20 })
  const output = `${done.stdout ?? ''}${done.stderr ?? ''}`
  const summary = output.split('\n').filter((l) => /(passed|failed|Tests|\u2718|Error:|Expected|Received)/.test(l)).slice(-12)
  // Tool output carries box-drawing and ellipsis characters; the record keeps ASCII only.
  const ascii = summary.map((l) => l.replace(/[^\x20-\x7e]+/g, ' ').trim())
  return { exit: done.status, seconds: (Date.now() - started) / 1000, summary: ascii }
}

function checks(spec, env) {
  return spec.checks.map((check) =>
    check.kind === 'unit'
      ? { ...check, ...run('npx', ['vitest', 'run', check.file]) }
      : { ...check, ...run('npx', ['playwright', 'test', check.file, '-g', check.grep, '--reporter=line'], env) },
  )
}

function falsify(name) {
  const spec = registry[name]
  if (!spec) throw new Error(`no falsifier ${name}`)
  const scratch = mkdtempSync(path.join(tmpdir(), `veldo-falsify-${name}-`))
  const originals = new Map()
  const env = {}
  const edits = []
  try {
    for (const edit of spec.edits) {
      let target
      if (edit.organ) {
        const organs = path.join(scratch, 'organs')
        if (!env.VELDO_ORGANS) cpSync(path.join(ROOT, '.veldo'), organs, { recursive: true })
        env.VELDO_ORGANS = organs
        target = path.join(organs, edit.organ)
      } else {
        target = path.join(UI, edit.file)
        if (!originals.has(target)) originals.set(target, readFileSync(target, 'utf8'))
      }
      const text = readFileSync(target, 'utf8')
      const count = text.split(edit.old).length - 1
      if (count !== 1) throw new Error(`${edit.file ?? edit.organ}: the edit's anchor occurs ${count} times`)
      const mutant = text.replace(edit.old, edit.new)
      writeFileSync(target, mutant)
      edits.push({ file: edit.file ?? `.veldo/${edit.organ}`, source_sha256: sha(text), mutant_sha256: sha(mutant), old: edit.old, new: edit.new })
    }
    // The package's own build script (type-check, then build), into a scratch directory.
    const built = run('npm', ['run', 'build', '--', '--outDir', path.join(scratch, 'dist'), '--emptyOutDir'])
    if (built.exit !== 0) throw new Error(`the falsified UI did not build: ${built.summary.join(' ')}`)
    const red = checks(spec, { ...env, VELDO_UI_DIST: path.join(scratch, 'dist') })
    for (const [file, text] of originals) writeFileSync(file, text)
    originals.clear()
    const green = checks(spec, {})
    const record = {
      schema: 'veldo.ui_falsifier_record/v1',
      case: name,
      criterion: spec.criterion,
      falsifier: spec.falsifier,
      commit: spawnSync('git', ['rev-parse', 'HEAD'], { cwd: ROOT, encoding: 'utf8' }).stdout.trim(),
      edits,
      red,
      green,
      red_as_required: red.every((c) => c.exit !== 0),
      green_as_required: green.every((c) => c.exit === 0),
    }
    mkdirSync(OUT, { recursive: true })
    writeFileSync(path.join(OUT, `${name}.json`), JSON.stringify(record, null, 2) + '\n')
    console.log(`${name}: red ${record.red_as_required ? 'as required' : 'NOT RED'}, green ${record.green_as_required ? 'as required' : 'NOT GREEN'}`)
    return record.red_as_required && record.green_as_required
  } finally {
    for (const [file, text] of originals) writeFileSync(file, text)
    rmSync(scratch, { recursive: true, force: true })
  }
}

const names = process.argv.slice(2).filter((a) => !a.startsWith('-'))
const all = process.argv.includes('--all') ? Object.keys(registry) : names
if (!all.length) {
  console.log(`usage: npm run falsify -- <case>|--all\ncases: ${Object.keys(registry).join(', ')}`)
  process.exit(64)
}
let ok = true
for (const name of all) ok = falsify(name) && ok
process.exit(ok ? 0 : 1)
