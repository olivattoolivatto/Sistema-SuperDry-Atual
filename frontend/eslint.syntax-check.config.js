const babelParser = require('@babel/eslint-parser');

module.exports = [
  {
    files: ['**/*.js', '**/*.jsx'],
    languageOptions: {
      parser: babelParser,
      parserOptions: {
        requireConfigFile: false,
        babelOptions: {
          presets: ['@babel/preset-react'],
        },
        ecmaVersion: 2021,
        sourceType: 'module',
      },
    },
    rules: {},
  },
];
