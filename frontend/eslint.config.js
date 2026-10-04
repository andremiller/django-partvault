import js from '@eslint/js'
import vue from 'eslint-plugin-vue'
import ts from 'typescript-eslint'
import globals from 'globals'

export default ts.config(
  { ignores: ['node_modules/**'] },
  js.configs.recommended,
  ...ts.configs.recommended,
  ...vue.configs['flat/recommended'],
  {
    files: ['**/*.{js,ts,vue}'],
    languageOptions: {
      globals: { ...globals.browser, ...globals.node },
      parserOptions: { parser: ts.parser },
    },
    rules: {
      'vue/multi-word-component-names': 'off',
      'vue/html-self-closing': ['error', { html: { void: 'always', normal: 'always', component: 'always' } }],
    },
  },
)
