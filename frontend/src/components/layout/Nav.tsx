import { NavLink } from 'react-router-dom'

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `px-4 py-2 rounded-md text-sm font-medium transition-colors ${
    isActive
      ? 'bg-blue-600 text-white'
      : 'text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
  }`

export default function Nav() {
  return (
    <nav className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-2">
        <span className="font-bold text-lg mr-4">IdleFramework</span>
        <NavLink to="/play" className={linkClass}>Play</NavLink>
        <NavLink to="/analyze" className={linkClass}>Analyze</NavLink>
        <NavLink to="/editor" className={linkClass}>Editor</NavLink>
        <a
          href="https://github.com/ac2522/IdleFramework"
          target="_blank"
          rel="noopener noreferrer"
          className="ml-auto text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
        >
          GitHub
        </a>
      </div>
    </nav>
  )
}
