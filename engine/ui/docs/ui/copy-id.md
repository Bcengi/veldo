# CopyId

An identifier a person copies (a dispatch id, a passkey id): set in mono on a sunken chip, broken
anywhere, with a Copy button that says "Copied" for two seconds. It writes only the clipboard.

## Props

| Prop | Type | Meaning |
|---|---|---|
| `value` | string | The identifier, shown and copied exactly |
| `label` | string | What it is, for the button's name: "Copy dispatch id" |
| `testid` | string, optional | `data-testid` on the value |

## When to use it

For ids the owner may need to paste into a terminal or a message. Put it behind a disclosure
("Dispatch id") when it is not what the screen is about; never make an id a screen's title.
