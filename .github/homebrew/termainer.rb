# Formula for homebrew-termainer tap
# Repo: https://github.com/AlanStefanov/homebrew-termainer
# Install: brew tap AlanStefanov/termainer && brew install termainer
#
# This file is updated automatically by publish.yml on every release.
# version: 0.4.0

class Termainer < Formula
  include Language::Python::Virtualenv

  desc "Container observability and operations directly from your terminal"
  homepage "https://github.com/AlanStefanov/termainer"
  url "https://files.pythonhosted.org/packages/source/t/termainer/termainer-0.4.0.tar.gz"
  sha256 "PLACEHOLDER_SHA256"
  license "MIT"

  depends_on "python@3.11"

  resource "textual" do
    url "https://files.pythonhosted.org/packages/source/t/textual/textual-3.5.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "rich" do
    url "https://files.pythonhosted.org/packages/source/r/rich/rich-14.0.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "pyyaml" do
    url "https://files.pythonhosted.org/packages/source/P/PyYAML/PyYAML-6.0.2.tar.gz"
    sha256 "PLACEHOLDER"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/termainer --version")
  end
end
