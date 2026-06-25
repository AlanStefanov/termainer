class Termainer < Formula
  desc "Container observability and operations directly from your terminal"
  homepage "https://github.com/AlanStefanov/termainer"
  url "https://github.com/AlanStefanov/termainer/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "REPLACE_ME"
  license "MIT"

  depends_on "python@3.11"

  def install
    venv = virtualenv_create(libexec, "python3.11")
    venv.pip_install resources
    venv.pip_install_and_link buildpath
  end

  test do
    assert_match "Termainer", shell_output("#{bin}/termainer --version")
  end
end
