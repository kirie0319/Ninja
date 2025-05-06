// Configure marked to use highlight.js for code blocks
marked.setOptions({
    highlight: function(code, lang) {
        const language = hljs.getLanguage(lang) ? lang : 'plaintext';
        return hljs.highlight(code, { language }).value;
    },
    langPrefix: 'hljs language-'
});

function parseMarkdown(text) {
    // Convert bold (**text** or __text__)
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/__(.*?)__/g, '<strong>$1</strong>');
    
    // Convert italic (*text* or _text_)
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
    text = text.replace(/_(.*?)_/g, '<em>$1</em>');
    
    // Convert strikethrough (~~text~~)
    text = text.replace(/~~(.*?)~~/g, '<del>$1</del>');
    
    // Convert code blocks (```language\ncode\n```)
    text = text.replace(/```(\w+)?\n([\s\S]*?)```/g, function(match, lang, code) {
        return `<pre class="bg-gray-100 rounded p-3 my-2 overflow-x-auto"><code class="language-${lang || ''}">${escapeHtml(code.trim())}</code></pre>`;
    });
    
    // Convert inline code (`code`)
    text = text.replace(/`([^`]+)`/g, '<code class="bg-gray-100 text-red-600 px-1 rounded">$1</code>');
    
    // Convert headers (# Header)
    text = text.replace(/^###### (.*?)$/gm, '<h6 class="text-base font-bold mt-4 mb-2">$1</h6>');
    text = text.replace(/^##### (.*?)$/gm, '<h5 class="text-lg font-bold mt-4 mb-2">$1</h5>');
    text = text.replace(/^#### (.*?)$/gm, '<h4 class="text-xl font-bold mt-4 mb-2">$1</h4>');
    text = text.replace(/^### (.*?)$/gm, '<h3 class="text-2xl font-bold mt-4 mb-2">$1</h3>');
    text = text.replace(/^## (.*?)$/gm, '<h2 class="text-3xl font-bold mt-4 mb-2">$1</h2>');
    text = text.replace(/^# (.*?)$/gm, '<h1 class="text-4xl font-bold mt-4 mb-2">$1</h1>');
    
    // Convert unordered lists (- item or * item)
    text = text.replace(/^(\s*)[*-] (.*)$/gm, function(match, indent, content) {
        const level = indent.length / 2;
        return `<li class="ml-${level * 4}">${content}</li>`;
    });
    
    // Wrap li elements in ul
    text = text.replace(/(<li.*?>.*?<\/li>)+/g, '<ul class="list-disc pl-5 my-2">$&</ul>');
    
    // Convert ordered lists (1. item)
    text = text.replace(/^(\s*)\d+\. (.*)$/gm, function(match, indent, content) {
        const level = indent.length / 2;
        return `<li class="ml-${level * 4}">${content}</li>`;
    });
    
    // Wrap ordered li elements in ol
    text = text.replace(/(?<!>)(<li.*?>.*?<\/li>)+(?![^<]*<\/ul>)/g, '<ol class="list-decimal pl-5 my-2">$&</ol>');
    
    // Convert block quotes (> text)
    text = text.replace(/^> (.*)$/gm, '<blockquote class="border-l-4 border-red-500 pl-4 my-2 italic">$1</blockquote>');
    
    // Convert horizontal rules (---, ***, ___)
    text = text.replace(/^(?:[-_*]){3,}$/gm, '<hr class="border-t border-gray-300 my-4">');
    
    // Convert paragraphs
    text = text.replace(/^(?!<[^>]+>)(.+)$/gm, '<p class="mb-2">$1</p>');
    
    // Convert links [text](url)
    text = text.replace(/\[([^\]]+)\]\(([^\)]+)\)/g, '<a href="$2" target="_blank" class="underline text-blue-600 hover:text-blue-800">$1</a>');
    
    // Convert autolinking for URLs
    const urlRegex = /(https?:\/\/[^\s<]+)/g;
    text = text.replace(urlRegex, '<a href="$1" target="_blank" class="underline text-blue-600 hover:text-blue-800">$1</a>');
    
    return text;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}