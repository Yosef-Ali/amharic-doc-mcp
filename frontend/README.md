# Amharic Document System - Frontend

> React + TypeScript frontend with CopilotKit and MCP integration

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Project Structure](#project-structure)
- [Development](#development)
- [Testing](#testing)
- [Building for Production](#building-for-production)

## 🌟 Overview

The frontend is a modern React application that provides:

- **CopilotKit Integration**: AI-powered document processing UI
- **MCP Client**: Full Model Context Protocol support
- **Real-time Updates**: WebSocket-based progress tracking
- **Responsive Design**: Mobile-first Tailwind CSS styling
- **Internationalization**: Support for Amharic and English
- **Type Safety**: Full TypeScript coverage

## 📦 Prerequisites

- Node.js 18.x or higher
- pnpm 8.x (recommended) or npm 9.x
- Backend API running (see [backend/README.md](../backend/README.md))

### Install pnpm (Recommended)

```bash
# Via npm
npm install -g pnpm

# Via Homebrew (macOS)
brew install pnpm

# Via curl (Linux/macOS)
curl -fsSL https://get.pnpm.io/install.sh | sh -
```

## 🚀 Installation

### Using pnpm (Recommended)

```bash
# Install dependencies
pnpm install
```

### Using npm

```bash
# Install dependencies
npm install
```

## ⚙️ Configuration

### 1. Create Environment File

```bash
cp .env.example .env.local
```

### 2. Edit `.env.local` with Your Settings

```env
# API Configuration
VITE_API_BASE_URL=http://localhost:8000
VITE_API_VERSION=v1
VITE_WS_URL=ws://localhost:8000

# MCP Configuration
VITE_MCP_ENDPOINT=http://localhost:8000/api/v1/mcp
VITE_MCP_WS_ENDPOINT=ws://localhost:8000/api/v1/mcp/ws

# CopilotKit Configuration
VITE_COPILOT_PUBLIC_API_KEY=  # Optional: for CopilotKit cloud features

# Application
VITE_APP_NAME=Amharic Document System
VITE_APP_VERSION=1.0.0
VITE_DEFAULT_LANGUAGE=en

# Features
VITE_ENABLE_OCR=true
VITE_ENABLE_BATCH_UPLOAD=true
VITE_ENABLE_EXPORT=true
VITE_ENABLE_SEARCH=true

# Upload Limits
VITE_MAX_FILE_SIZE=104857600  # 100MB in bytes
VITE_ALLOWED_FILE_TYPES=.pdf,.png,.jpg,.jpeg,.docx,.doc,.csv,.txt,.html

# UI
VITE_THEME=light  # light, dark, or auto
VITE_ITEMS_PER_PAGE=20
```

## 🏃 Running the Application

### Development Mode

```bash
# Start development server
pnpm dev

# Or with npm
npm run dev
```

The application will be available at http://localhost:3000

### Development with Backend

Ensure the backend is running first:

```bash
# In backend directory
uvicorn src.main:app --reload

# Then in frontend directory
pnpm dev
```

## 📁 Project Structure

```
frontend/
├── src/
│   ├── components/           # React components
│   │   ├── common/          # Reusable components
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Card.tsx
│   │   │   └── Modal.tsx
│   │   ├── document/        # Document-related components
│   │   │   ├── DocumentUpload.tsx
│   │   │   ├── DocumentList.tsx
│   │   │   ├── DocumentViewer.tsx
│   │   │   └── DocumentCard.tsx
│   │   ├── processing/      # Processing UI
│   │   │   ├── ProcessingStatus.tsx
│   │   │   ├── ProgressBar.tsx
│   │   │   └── JobQueue.tsx
│   │   ├── search/          # Search components
│   │   │   ├── SearchBar.tsx
│   │   │   ├── SearchResults.tsx
│   │   │   └── SearchFilters.tsx
│   │   └── layout/          # Layout components
│   │       ├── Header.tsx
│   │       ├── Sidebar.tsx
│   │       └── Footer.tsx
│   ├── hooks/               # Custom React hooks
│   │   ├── useAuth.ts
│   │   ├── useDocuments.ts
│   │   ├── useProcessing.ts
│   │   ├── useSearch.ts
│   │   ├── useWebSocket.ts
│   │   └── useMCP.ts
│   ├── services/            # API services
│   │   ├── api.ts          # Axios instance
│   │   ├── mcp.ts          # MCP client
│   │   ├── documents.ts    # Document operations
│   │   ├── processing.ts   # Processing operations
│   │   └── auth.ts         # Authentication
│   ├── contexts/            # React contexts
│   │   ├── AuthContext.tsx
│   │   ├── MCPContext.tsx
│   │   └── ThemeContext.tsx
│   ├── i18n/               # Internationalization
│   │   ├── index.ts
│   │   ├── en.json
│   │   └── am.json
│   ├── types/              # TypeScript types
│   │   ├── document.ts
│   │   ├── processing.ts
│   │   ├── mcp.ts
│   │   └── api.ts
│   ├── utils/              # Utility functions
│   │   ├── formatters.ts
│   │   ├── validators.ts
│   │   └── helpers.ts
│   ├── styles/             # Global styles
│   │   └── globals.css
│   ├── App.tsx             # Main app component
│   └── main.tsx            # Entry point
├── public/                 # Static assets
├── tests/                  # Test files
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── .eslintrc.cjs          # ESLint config
├── .prettierrc            # Prettier config
├── tailwind.config.js     # Tailwind config
├── tsconfig.json          # TypeScript config
├── vite.config.ts         # Vite config
└── package.json           # Dependencies
```

## 🔧 Development

### Code Style

We enforce code quality with:

```bash
# Lint code
pnpm lint

# Fix linting issues
pnpm lint:fix

# Format code
pnpm format

# Type check
pnpm type-check
```

### Component Development

#### Creating a New Component

```bash
# Create component directory
mkdir -p src/components/feature-name

# Create component file
touch src/components/feature-name/FeatureName.tsx
```

Example component:
```tsx
// src/components/document/DocumentCard.tsx
import { FC } from 'react';
import { Document } from '@/types/document';
import { Card } from '@/components/common/Card';

interface DocumentCardProps {
  document: Document;
  onSelect?: (document: Document) => void;
}

export const DocumentCard: FC<DocumentCardProps> = ({ 
  document, 
  onSelect 
}) => {
  return (
    <Card 
      onClick={() => onSelect?.(document)}
      className="hover:shadow-lg transition-shadow"
    >
      <h3 className="font-semibold">{document.filename}</h3>
      <p className="text-sm text-gray-600">{document.status}</p>
    </Card>
  );
};
```

### Custom Hooks

#### Creating a Custom Hook

```tsx
// src/hooks/useDocuments.ts
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { documentsService } from '@/services/documents';

export const useDocuments = () => {
  const queryClient = useQueryClient();

  const { data: documents, isLoading } = useQuery(
    'documents',
    documentsService.getAll
  );

  const uploadMutation = useMutation(
    documentsService.upload,
    {
      onSuccess: () => {
        queryClient.invalidateQueries('documents');
      }
    }
  );

  return {
    documents,
    isLoading,
    uploadDocument: uploadMutation.mutate,
    isUploading: uploadMutation.isLoading
  };
};
```

### MCP Integration

#### Using MCP Tools

```tsx
// src/components/document/DocumentUpload.tsx
import { useMCP } from '@/hooks/useMCP';

export const DocumentUpload = () => {
  const { executeTool } = useMCP();

  const handleUpload = async (file: File) => {
    const result = await executeTool('upload_document', {
      file_data: await fileToBase64(file),
      filename: file.name,
      content_type: file.type
    });

    if (result.success) {
      console.log('Upload successful:', result.document_id);
    }
  };

  return (
    <div>
      <input type="file" onChange={(e) => handleUpload(e.target.files[0])} />
    </div>
  );
};
```

### WebSocket Integration

```tsx
// src/hooks/useWebSocket.ts
import { useEffect, useState } from 'react';

export const useWebSocket = (url: string) => {
  const [messages, setMessages] = useState([]);
  const [ws, setWs] = useState<WebSocket | null>(null);

  useEffect(() => {
    const websocket = new WebSocket(url);
    
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setMessages(prev => [...prev, data]);
    };

    setWs(websocket);

    return () => websocket.close();
  }, [url]);

  return { messages, ws };
};
```

### Internationalization

```tsx
// Using i18n in components
import { useTranslation } from 'react-i18next';

export const DocumentList = () => {
  const { t } = useTranslation();

  return (
    <div>
      <h2>{t('documents.title')}</h2>
      <p>{t('documents.description')}</p>
    </div>
  );
};
```

Add translations in `src/i18n/en.json`:
```json
{
  "documents": {
    "title": "Documents",
    "description": "Manage your documents"
  }
}
```

## 🧪 Testing

### Run All Tests

```bash
pnpm test
```

### Run Tests with UI

```bash
pnpm test:ui
```

### Run Tests with Coverage

```bash
pnpm test:coverage
```

### Unit Tests

```tsx
// tests/unit/components/DocumentCard.test.tsx
import { render, screen } from '@testing-library/react';
import { DocumentCard } from '@/components/document/DocumentCard';

describe('DocumentCard', () => {
  it('renders document information', () => {
    const document = {
      id: '1',
      filename: 'test.pdf',
      status: 'completed'
    };

    render(<DocumentCard document={document} />);
    
    expect(screen.getByText('test.pdf')).toBeInTheDocument();
    expect(screen.getByText('completed')).toBeInTheDocument();
  });
});
```

### Integration Tests

```tsx
// tests/integration/DocumentUpload.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DocumentUpload } from '@/components/document/DocumentUpload';

describe('DocumentUpload Integration', () => {
  it('uploads document successfully', async () => {
    render(<DocumentUpload />);
    
    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
    const input = screen.getByLabelText(/upload/i);
    
    await userEvent.upload(input, file);
    
    await waitFor(() => {
      expect(screen.getByText(/success/i)).toBeInTheDocument();
    });
  });
});
```

## 🏗️ Building for Production

### Create Production Build

```bash
# Build with pnpm
pnpm build

# Or with npm
npm run build
```

The build output will be in the `dist/` directory.

### Preview Production Build

```bash
pnpm preview
```

### Build with Environment

```bash
# Production
NODE_ENV=production pnpm build

# Staging
NODE_ENV=staging pnpm build
```

## 📦 Docker Build

### Build Docker Image

```bash
# From frontend directory
docker build -t amharic-doc-frontend:latest .

# Or from root directory
docker build -f frontend/Dockerfile -t amharic-doc-frontend:latest ./frontend
```

### Run Docker Container

```bash
docker run -p 3000:3000 \
  -e VITE_API_BASE_URL=http://backend:8000 \
  amharic-doc-frontend:latest
```

## 🎨 Styling with Tailwind

### Using Tailwind Classes

```tsx
export const Button = ({ children, onClick }) => (
  <button
    onClick={onClick}
    className="px-4 py-2 bg-blue-600 text-white rounded-lg 
               hover:bg-blue-700 transition-colors duration-200
               focus:outline-none focus:ring-2 focus:ring-blue-500"
  >
    {children}
  </button>
);
```

### Custom Tailwind Configuration

Edit `tailwind.config.js`:
```js
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: '#1E40AF',
        secondary: '#7C3AED',
      },
      fontFamily: {
        amharic: ['Noto Sans Ethiopic', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
```

## 🐛 Debugging

### Browser DevTools

1. Open browser DevTools (F12)
2. Go to Sources tab
3. Set breakpoints in your code
4. Trigger the action to debug

### VS Code Debugging

Create `.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "type": "chrome",
      "request": "launch",
      "name": "Launch Chrome",
      "url": "http://localhost:3000",
      "webRoot": "${workspaceFolder}/src"
    }
  ]
}
```

### React DevTools

Install React DevTools extension for Chrome/Firefox to inspect component hierarchy and props.

## 🚀 Performance Optimization

### Code Splitting

```tsx
// Lazy load components
import { lazy, Suspense } from 'react';

const DocumentViewer = lazy(() => import('./components/document/DocumentViewer'));

function App() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <DocumentViewer />
    </Suspense>
  );
}
```

### Memoization

```tsx
import { memo, useMemo, useCallback } from 'react';

export const DocumentList = memo(({ documents }) => {
  const sortedDocuments = useMemo(
    () => documents.sort((a, b) => a.name.localeCompare(b.name)),
    [documents]
  );

  const handleSelect = useCallback((doc) => {
    console.log('Selected:', doc);
  }, []);

  return (
    <div>
      {sortedDocuments.map(doc => (
        <DocumentCard key={doc.id} document={doc} onSelect={handleSelect} />
      ))}
    </div>
  );
});
```

## 🔒 Security Best Practices

1. **Never commit `.env.local`** - Contains sensitive keys
2. **Validate all user inputs** - Use validation libraries
3. **Sanitize HTML** - Use DOMPurify for user-generated content
4. **Use HTTPS in production** - Configure nginx/reverse proxy
5. **Implement CSRF protection** - For state-changing operations

## 📱 Responsive Design

```tsx
// Mobile-first responsive component
export const DocumentGrid = () => (
  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
    {/* Document cards */}
  </div>
);

// Responsive hook
const useMediaQuery = (query: string) => {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    const media = window.matchMedia(query);
    setMatches(media.matches);

    const listener = () => setMatches(media.matches);
    media.addEventListener('change', listener);
    return () => media.removeEventListener('change', listener);
  }, [query]);

  return matches;
};

// Usage
const isMobile = useMediaQuery('(max-width: 768px)');
```

## 🤝 Contributing

Please read the main [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

## 📝 License

MIT License - see [LICENSE](../LICENSE) for details.

## 🆘 Support

- **Documentation**: Check [docs/](../docs/)
- **Issues**: [GitHub Issues](https://github.com/your-org/amharic-doc-mcp/issues)
- **Email**: support@amharic-docs.ai
