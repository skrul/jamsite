const path = require('path');
const CopyPlugin = require('copy-webpack-plugin');

module.exports = {
    entry: {
        'viewer': './src/viewer.js',
        'pdf.worker': 'pdfjs-dist/build/pdf.worker.mjs',
    },
    output: {
        filename: '[name].bundle.js',
        path: path.resolve(__dirname, 'dist/js'),
    },
    module: {
        rules: [

            {
                test: /\.m?js$/,
                exclude: /node_modules\/(?!pdfjs-dist)/,
                // exclude: /node_modules/,
                use: {
                    loader: 'babel-loader',
                    options: {
                        presets: [
                            ['@babel/preset-env', {
                                useBuiltIns: 'usage',
                                corejs: { version: 3, proposals: true },
                                targets: {
                                    safari: '11',
                                    ios: '11'
                                },
                                debug: true
                            }]
                        ],
                        plugins: [
                            '@babel/plugin-transform-runtime'
                        ]
                    }
                }
            }
        ]
    },
    plugins: [
        new CopyPlugin({
            patterns: [
                {
                    from: 'node_modules/pdfjs-dist/web/pdf_viewer.css',
                    to: '../css/viewer.css'
                },
            ],
        }),
    ],
    optimization: {
        minimize: false
    },
};