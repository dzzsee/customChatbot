import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface Props {
  children: string
  streaming?: boolean
}

export function MarkdownView({ children, streaming = false }: Props) {
  return (
    <div className={`prose-nemotron ${streaming ? 'cursor-blink' : ''}`}>
      <Markdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ children: linkChildren, ...props }) => (
            <a {...props} target="_blank" rel="noreferrer noopener">
              {linkChildren}
            </a>
          ),
        }}
      >
        {children}
      </Markdown>
    </div>
  )
}
