const path = require('path');

module.exports = {
    entry: {
        'viewer': './src/viewer.js',
        'pdf.worker': 'pdfjs-dist/build/pdf.worker.mjs',
      },
  output: {
    filename: '[name].bundle.js',
    path: path.resolve(__dirname, 'dist/js'),
  },
};